import asyncio
import logging
import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional, Literal

from config import config
from freefire_client import FreeFireApiClient, FreeFireMockClient, BaseFreeFireClient
from guild_tracker import GuildTracker
from channel_manager import ChannelManager
from player_tracker import PlayerTracker
from keep_alive import start_keep_alive_server, self_ping_task
from discord_embeds import (
    build_status_change_embed,
    build_member_joined_embed,
    build_member_left_embed,
    build_invite_sent_embed,
    build_ex_member_new_guild_embed,
    build_player_profile_embed
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("DiscordBot")

# Set up Discord intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# State engines
tracker = GuildTracker()
channel_mgr = ChannelManager(default_channel_id=config.DISCORD_CHANNEL_ID)
player_tracker = PlayerTracker(my_guild_id=config.FF_GUILD_ID or "3008075139", my_guild_name="HWK X6")

# Free Fire client
ff_client: BaseFreeFireClient
if config.MOCK_MODE or not config.FF_ACCESS_TOKEN:
    logger.info("Starting Free Fire client in SIMULATION / MOCK MODE.")
    ff_client = FreeFireMockClient(guild_id=config.FF_GUILD_ID or "3008075139")
else:
    logger.info("Starting Free Fire client in LIVE API MODE.")
    ff_client = FreeFireApiClient(
        gateway_url=config.FF_API_GATEWAY_URL or "http://localhost:8080",
        access_token=config.FF_ACCESS_TOKEN,
        account_uid=config.FF_BOT_UID,
        region=config.FF_REGION,
        api_key=config.FF_API_KEY
    )

async def deliver_embed(category: str, embed: discord.Embed):
    """Deliver embed to the dedicated channel for that category, or fallback."""
    channel_id = channel_mgr.get_channel_id(category)
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                await channel.send(embed=embed)
                return
            except Exception as e:
                logger.error(f"Failed to send to #{channel.name} ({channel_id}): {e}")

    # Fallback to Webhook if channel couldn't receive it
    if config.DISCORD_WEBHOOK_URL:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(config.DISCORD_WEBHOOK_URL, session=session)
            try:
                await webhook.send(embed=embed)
            except Exception as e:
                logger.error(f"Failed to send embed to fallback Webhook: {e}")


@tasks.loop(seconds=config.POLL_INTERVAL_SECONDS)
async def poll_guild_status():
    """Periodic task that fetches guild snapshot, calculates diffs, and alerts dedicated channels."""
    try:
        guild_id = config.FF_GUILD_ID or "3008075139"
        snapshot = await ff_client.get_guild_snapshot(guild_id)
        if not snapshot:
            return

        status_events, joined_events, left_events, invite_events = tracker.process_snapshot(snapshot)

        # 1. Playing / In Match Channel
        for event in status_events:
            embed = build_status_change_embed(event)
            await deliver_embed("playing", embed)
            await asyncio.sleep(0.5)

        # 2. Join Approvals Channel
        for event in joined_events:
            embed = build_member_joined_embed(event)
            await deliver_embed("joins", embed)
            await asyncio.sleep(0.5)

        # 3. Invites Channel
        for event in invite_events:
            embed = build_invite_sent_embed(event)
            await deliver_embed("invites", embed)
            await asyncio.sleep(0.5)

        # 4. Member Departures Channel (Leaves / Kicks)
        for event in left_events:
            player_tracker.record_departure(event.uid, event.nickname)
            embed = build_member_left_embed(event)
            await deliver_embed("leaves", embed)
            await asyncio.sleep(0.5)

        # 5. Check if any departed member has joined a new guild
        new_guild_events = player_tracker.check_for_new_guilds()
        for ev in new_guild_events:
            embed = build_ex_member_new_guild_embed(ev)
            await deliver_embed("leaves", embed)
            await asyncio.sleep(0.5)

    except Exception as e:
        logger.error(f"Error during guild poll loop: {e}", exc_info=True)


@bot.event
async def on_ready():
    logger.info(f"Discord Bot logged in as {bot.user} (ID: {bot.user.id})")
    
    # Clean up any duplicate guild commands so each command only appears ONCE
    for guild in bot.guilds:
        try:
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
        except Exception:
            pass

    # Single global command registration
    try:
        synced = await bot.tree.sync()
        logger.info(f"Slash Commands: {len(synced)} active commands registered.")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")

    if not poll_guild_status.is_running():
        poll_guild_status.start()
        logger.info(f"Started guild monitoring task (Interval: {config.POLL_INTERVAL_SECONDS}s).")

    # Start Render 24/7 Keep-Alive Web Server & Self-Pinger
    try:
        await start_keep_alive_server()
        bot.loop.create_task(self_ping_task())
    except Exception as e:
        logger.warning(f"Keep-Alive server notice: {e}")


# ====================================================================
# SLASH COMMANDS
# ====================================================================

@bot.tree.command(name="status", description="Show full overview of your Free Fire guild")
async def slash_status(interaction: discord.Interaction):
    """Show current guild overview."""
    guild_id = config.FF_GUILD_ID or "3008075139"
    snapshot = await ff_client.get_guild_snapshot(guild_id)
    if not snapshot:
        await interaction.response.send_message("⚠️ Unable to fetch guild data.", ephemeral=True)
        return

    playing_count = sum(1 for m in snapshot.members if "Playing" in m.state.value or "Match" in m.state.value)
    lobby_count = sum(1 for m in snapshot.members if m.state.value == "Online (Lobby)")
    offline_count = sum(1 for m in snapshot.members if m.state.value == "Offline")

    embed = discord.Embed(
        title=f"🛡️ Guild Overview: {snapshot.guild_name}",
        description=f"Guild ID: `{snapshot.guild_id}` • Region: `{config.FF_REGION}`",
        color=0x3498DB
    )
    embed.add_field(name="Members", value=f"👥 {snapshot.member_count}/{snapshot.max_members}", inline=True)
    embed.add_field(name="Guild Level", value=f"⭐ Level {snapshot.guild_level}", inline=True)
    embed.add_field(name="Activity Breakdown", value=(
        f"🟢 In Match: **{playing_count}**\n"
        f"🔵 In Lobby: **{lobby_count}**\n"
        f"⚪ Offline: **{offline_count}**"
    ), inline=False)
    embed.set_footer(text="Free Fire Guild Activity Monitor")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="playing", description="List guild members currently playing CS or Battle Royale")
async def slash_playing(interaction: discord.Interaction):
    """List members in match."""
    guild_id = config.FF_GUILD_ID or "3008075139"
    snapshot = await ff_client.get_guild_snapshot(guild_id)
    if not snapshot:
        await interaction.response.send_message("⚠️ Unable to fetch guild data.", ephemeral=True)
        return

    playing_members = [m for m in snapshot.members if "Playing" in m.state.value or "Match" in m.state.value]
    if not playing_members:
        await interaction.response.send_message("ℹ️ No guild members are currently inside a match.", ephemeral=True)
        return

    desc = "\n".join([f"• **{m.nickname}** (`{m.uid}`) - {m.game_mode or m.state.value}" for m in playing_members])
    embed = discord.Embed(
        title="🎮 Guild Members Currently In Match",
        description=desc,
        color=0x2ECC71
    )
    embed.set_footer(text="Live Free Fire Match Activity")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="track_player", description="Check player profile and which guild they currently belong to by UID")
@app_commands.describe(uid="Free Fire Player UID (e.g. 15209232058)")
async def slash_track_player(interaction: discord.Interaction, uid: str):
    """Look up a player by UID and show their current & previous guild."""
    await interaction.response.defer()
    clean_uid = uid.strip()
    profile = await player_tracker.lookup_player(clean_uid)
    if not profile:
        await interaction.followup.send(f"⚠️ Could not find player data for UID `{clean_uid}`.")
        return

    embed = build_player_profile_embed(profile)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="set_channel", description="Set a dedicated channel for a specific log type")
@app_commands.describe(
    category="Type of log (playing, invites, joins, leaves)",
    channel="The Discord channel where these logs should go"
)
async def slash_set_channel(
    interaction: discord.Interaction,
    category: Literal["playing", "invites", "joins", "leaves"],
    channel: discord.TextChannel
):
    """Assign a channel for a log category."""
    success = channel_mgr.set_channel(category, channel.id)
    if success:
        await interaction.response.send_message(
            f"✅ **{category.capitalize()} Logs** will now be sent to {channel.mention} (ID: `{channel.id}`)."
        )
    else:
        await interaction.response.send_message(f"❌ Failed to configure channel for `{category}`.", ephemeral=True)


@bot.tree.command(name="channels", description="View current channel configuration for all log types")
async def slash_channels(interaction: discord.Interaction):
    """View active channel routing."""
    embed = discord.Embed(
        title="📋 Dedicated Log Channels Configuration",
        color=0x3498DB
    )
    for cat in ("playing", "invites", "joins", "leaves"):
        cid = channel_mgr.get_channel_id(cat)
        ch = bot.get_channel(cid)
        mention = ch.mention if ch else f"`ID: {cid}`" if cid else "*Not Configured (Using Default)*"
        
        icons = {
            "playing": "🎮 Playing / In Match",
            "invites": "✉️ Friend Invitations",
            "joins": "📥 Joins & Approvals",
            "leaves": "📤 Leaves & New Guild Tracking"
        }
        embed.add_field(name=icons[cat], value=mention, inline=False)
    
    embed.set_footer(text="Use /set_channel to customize where each log is delivered.")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="setup_channels", description="Automatically create dedicated logging channels in your Discord server")
async def slash_setup_channels(interaction: discord.Interaction):
    """Automatically create dedicated channels in the server."""
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ This command must be run inside a Discord server.", ephemeral=True)
        return

    # Check bot permissions
    bot_member = guild.get_member(bot.user.id)
    if not bot_member.guild_permissions.manage_channels:
        await interaction.response.send_message(
            "⚠️ Bot lacks `Manage Channels` permission. Please grant the bot `Manage Channels` or create channels manually and use `/set_channel`.",
            ephemeral=True
        )
        return

    await interaction.response.defer()
    
    channel_specs = [
        ("playing", "🎮・playing-status", "Live Free Fire player match status (CS/BR/Lobby)"),
        ("invites", "✉・guild-invites", "Friend invitations sent by guild members"),
        ("joins", "📥・guild-joins", "New members joined & which officer approved them"),
        ("leaves", "📤・guild-leaves", "Members left, kicked, or joined another guild")
    ]

    created = []
    for cat_key, ch_name, topic in channel_specs:
        existing = discord.utils.get(guild.text_channels, name=ch_name)
        if not existing:
            new_ch = await guild.create_text_channel(name=ch_name, topic=topic)
            channel_mgr.set_channel(cat_key, new_ch.id)
            created.append(new_ch.mention)
        else:
            channel_mgr.set_channel(cat_key, existing.id)
            created.append(f"{existing.mention} *(already existed)*")

    await interaction.followup.send(
        f"✅ **Channels Configured Successfully!**\n" + "\n".join(created) + "\n\nLogs are now routed to their dedicated channels!"
    )


def main():
    if not config.DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN missing in .env")
        return
    bot.run(config.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
