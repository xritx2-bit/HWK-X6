import asyncio
import logging
import discord
from discord.ext import commands, tasks

from config import config
from freefire_client import FreeFireApiClient, FreeFireMockClient, BaseFreeFireClient
from guild_tracker import GuildTracker
from discord_embeds import (
    build_status_change_embed,
    build_member_joined_embed,
    build_member_left_embed,
    build_invite_sent_embed
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
tracker = GuildTracker()

# Initialize Free Fire client based on config
ff_client: BaseFreeFireClient
if config.MOCK_MODE or not config.FF_ACCESS_TOKEN:
    logger.info("Starting Free Fire client in SIMULATION / MOCK MODE.")
    ff_client = FreeFireMockClient(guild_id=config.FF_GUILD_ID or "772183921")
else:
    logger.info("Starting Free Fire client in LIVE API MODE.")
    ff_client = FreeFireApiClient(
        gateway_url=config.FF_API_GATEWAY_URL or "http://localhost:8080",
        access_token=config.FF_ACCESS_TOKEN,
        account_uid=config.FF_BOT_UID,
        region=config.FF_REGION,
        api_key=config.FF_API_KEY
    )

async def send_to_channel_or_webhook(embed: discord.Embed):
    """Deliver embed to Discord channel or fallback webhook."""
    delivered = False
    
    # Send via Discord bot channel if configured
    if config.DISCORD_CHANNEL_ID:
        channel = bot.get_channel(config.DISCORD_CHANNEL_ID)
        if channel:
            try:
                await channel.send(embed=embed)
                delivered = True
            except Exception as e:
                logger.error(f"Failed to send embed to Discord channel {config.DISCORD_CHANNEL_ID}: {e}")

    # Fallback to Webhook if provided
    if not delivered and config.DISCORD_WEBHOOK_URL:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(config.DISCORD_WEBHOOK_URL, session=session)
            try:
                await webhook.send(embed=embed)
                delivered = True
            except Exception as e:
                logger.error(f"Failed to send embed to Discord Webhook: {e}")

    if not delivered:
        logger.warning("Notification generated, but no valid Discord Channel ID or Webhook URL configured to receive it.")


@tasks.loop(seconds=config.POLL_INTERVAL_SECONDS)
async def poll_guild_status():
    """Periodic task that fetches guild snapshot, calculates diffs, and alerts Discord."""
    try:
        guild_id = config.FF_GUILD_ID or "772183921"
        snapshot = await ff_client.get_guild_snapshot(guild_id)
        if not snapshot:
            logger.warning("Could not retrieve guild snapshot from Free Fire client.")
            return

        status_events, joined_events, left_events, invite_events = tracker.process_snapshot(snapshot)

        # 1. Alert Status Changes (playing BR, CS, in lobby)
        for event in status_events:
            embed = build_status_change_embed(event)
            await send_to_channel_or_webhook(embed)
            await asyncio.sleep(0.5)

        # 2. Alert Member Joined & Approvals
        for event in joined_events:
            embed = build_member_joined_embed(event)
            await send_to_channel_or_webhook(embed)
            await asyncio.sleep(0.5)

        # 3. Alert Member Leaves / Kicks
        for event in left_events:
            embed = build_member_left_embed(event)
            await send_to_channel_or_webhook(embed)
            await asyncio.sleep(0.5)

        # 4. Alert Guild Invitations Sent
        for event in invite_events:
            embed = build_invite_sent_embed(event)
            await send_to_channel_or_webhook(embed)
            await asyncio.sleep(0.5)

    except Exception as e:
        logger.error(f"Error during guild poll loop: {e}", exc_info=True)


@bot.event
async def on_ready():
    logger.info(f"Discord Bot logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} application commands.")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")

    if not poll_guild_status.is_running():
        poll_guild_status.start()
        logger.info(f"Started guild monitoring task (Interval: {config.POLL_INTERVAL_SECONDS}s).")


@bot.command(name="status")
async def cmd_status(ctx: commands.Context):
    """Show current guild overview."""
    guild_id = config.FF_GUILD_ID or "772183921"
    snapshot = await ff_client.get_guild_snapshot(guild_id)
    if not snapshot:
        await ctx.send("⚠️ Unable to fetch guild data from Free Fire service.")
        return

    playing_count = sum(1 for m in snapshot.members if "Playing" in m.state.value or "Match" in m.state.value)
    lobby_count = sum(1 for m in snapshot.members if m.state.value == "Online (Lobby)")
    offline_count = sum(1 for m in snapshot.members if m.state.value == "Offline")

    embed = discord.Embed(
        title=f"🛡️ Guild Overview: {snapshot.guild_name}",
        color=0x3498DB
    )
    embed.add_field(name="Total Members", value=f"{snapshot.member_count}/{snapshot.max_members}", inline=True)
    embed.add_field(name="Guild Level", value=f"Level {snapshot.guild_level}", inline=True)
    embed.add_field(name="Status Breakdown", value=(
        f"🟢 In Match: **{playing_count}**\n"
        f"🔵 In Lobby: **{lobby_count}**\n"
        f"⚪ Offline: **{offline_count}**"
    ), inline=False)
    await ctx.send(embed=embed)


@bot.command(name="playing")
async def cmd_playing(ctx: commands.Context):
    """List all guild members currently in a match."""
    guild_id = config.FF_GUILD_ID or "772183921"
    snapshot = await ff_client.get_guild_snapshot(guild_id)
    if not snapshot:
        await ctx.send("⚠️ Unable to fetch guild data.")
        return

    playing_members = [m for m in snapshot.members if "Playing" in m.state.value or "Match" in m.state.value]
    if not playing_members:
        await ctx.send("ℹ️ No guild members are currently playing matches.")
        return

    desc = "\n".join([f"• **{m.nickname}** (`{m.uid}`) - {m.game_mode or m.state.value}" for m in playing_members])
    embed = discord.Embed(
        title="🎮 Members Currently In Match",
        description=desc,
        color=0x2ECC71
    )
    await ctx.send(embed=embed)


def main():
    if not config.DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN is not configured! Please set it in your .env or config.json file.")
        print("\n[!] Setup Note: Please edit .env with your DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID.")
        return

    bot.run(config.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
