from datetime import datetime
import discord
from models import (
    StatusChangeEvent,
    MemberJoinedEvent,
    MemberLeftEvent,
    InviteSentEvent,
    MemberState
)

# Color constants
COLOR_PLAYING = 0x2ECC71      # Vibrant Green
COLOR_LOBBY = 0x3498DB        # Light Blue
COLOR_OFFLINE = 0x95A5A6      # Grey
COLOR_JOINED = 0x1ABC9C       # Teal
COLOR_LEFT = 0xE74C3C         # Red
COLOR_INVITE = 0xF39C12       # Amber / Orange

FREE_FIRE_ICON_URL = "https://play-lh.googleusercontent.com/47s91mYk6v8gQeC6g61CqjB6l0Vz8oY1w8zC5n0c7c0b0a8e=s256"

def build_status_change_embed(event: StatusChangeEvent) -> discord.Embed:
    member = event.member
    is_now_playing = "Playing" in event.new_state.value or "Match" in event.new_state.value
    
    if is_now_playing:
        color = COLOR_PLAYING
        title = "🎮 Free Fire Guild: Player In Match"
        desc = f"**{member.nickname}** is now in a match!"
    elif event.new_state == MemberState.ONLINE:
        color = COLOR_LOBBY
        title = "🛋️ Free Fire Guild: Back to Lobby"
        desc = f"**{member.nickname}** returned to the lobby / team."
    else:
        color = COLOR_OFFLINE
        title = "🌙 Free Fire Guild: Member Offline"
        desc = f"**{member.nickname}** went offline."

    embed = discord.Embed(
        title=title,
        description=desc,
        color=color,
        timestamp=event.timestamp
    )
    embed.set_author(name="Free Fire Guild Monitor", icon_url=FREE_FIRE_ICON_URL)
    embed.add_field(name="Player", value=f"`{member.nickname}`", inline=True)
    embed.add_field(name="UID", value=f"`{member.uid}`", inline=True)
    embed.add_field(name="Role", value=f"`{member.role}`", inline=True)
    
    if member.game_mode:
        embed.add_field(name="Mode", value=f"`{member.game_mode}`", inline=True)
    
    embed.add_field(name="Previous State", value=f"`{event.old_state.value}`", inline=True)
    embed.add_field(name="New State", value=f"**{event.new_state.value}**", inline=True)
    embed.set_footer(text="Free Fire Guild Activity Tracker")
    return embed


def build_member_joined_embed(event: MemberJoinedEvent) -> discord.Embed:
    embed = discord.Embed(
        title="📥 Free Fire Guild: Member Joined & Approved!",
        description=f"A new player has officially entered the guild through approval.",
        color=COLOR_JOINED,
        timestamp=event.timestamp
    )
    embed.set_author(name="Guild Invitation & Approval Log", icon_url=FREE_FIRE_ICON_URL)
    embed.add_field(name="New Member", value=f"**{event.nickname}**", inline=True)
    embed.add_field(name="Member UID", value=f"`{event.uid}`", inline=True)
    
    if event.approved_by_name or event.approved_by_uid:
        officer_text = f"**{event.approved_by_name or 'Unknown'}** (`{event.approved_by_uid or 'N/A'}`)"
    else:
        officer_text = "*Approved via Guild Approval Queue*"
        
    embed.add_field(name="Accepted / Approved By", value=officer_text, inline=False)
    embed.set_footer(text="Guild Security & Membership Audit")
    return embed


def build_member_left_embed(event: MemberLeftEvent) -> discord.Embed:
    action = "kicked from" if event.is_kick else "left"
    embed = discord.Embed(
        title=f"📤 Free Fire Guild: Member {action.capitalize()}",
        description=f"**{event.nickname}** has {action} the guild.",
        color=COLOR_LEFT,
        timestamp=event.timestamp
    )
    embed.set_author(name="Guild Membership Log", icon_url=FREE_FIRE_ICON_URL)
    embed.add_field(name="Member", value=f"`{event.nickname}`", inline=True)
    embed.add_field(name="UID", value=f"`{event.uid}`", inline=True)
    if event.kicked_by_name:
        embed.add_field(name="Kicked By", value=f"`{event.kicked_by_name}` (`{event.kicked_by_uid}`)", inline=False)
    embed.set_footer(text="Guild Membership Audit")
    return embed


def build_invite_sent_embed(event: InviteSentEvent) -> discord.Embed:
    embed = discord.Embed(
        title="✉️ Free Fire Guild: Guild Invite Sent!",
        description=f"A guild member has sent an invitation to their friend.",
        color=COLOR_INVITE,
        timestamp=event.timestamp
    )
    embed.set_author(name="Guild Invitation Tracker", icon_url=FREE_FIRE_ICON_URL)
    embed.add_field(name="Invited By (Member)", value=f"**{event.inviter_name}** (`{event.inviter_uid}`)", inline=False)
    target_info = f"`{event.target_uid}`"
    if event.target_name:
        target_info = f"**{event.target_name}** ({target_info})"
    embed.add_field(name="Invited Friend (Target UID)", value=target_info, inline=False)
    embed.add_field(name="Status", value="*Pending Approval upon Acceptance*", inline=False)
    embed.set_footer(text="Guild Invite Tracking")
    return embed


def build_ex_member_new_guild_embed(event) -> discord.Embed:
    embed = discord.Embed(
        title="🔄 Free Fire Tracker: Ex-Member Joined New Guild!",
        description=f"A former guild member has joined a new guild.",
        color=0x9B59B6,  # Purple
        timestamp=event.timestamp
    )
    embed.set_author(name="Guild Migration Monitor", icon_url=FREE_FIRE_ICON_URL)
    embed.add_field(name="Player", value=f"**{event.nickname}**", inline=True)
    embed.add_field(name="UID", value=f"`{event.uid}`", inline=True)
    embed.add_field(name="Previous Guild", value=f"{event.previous_guild_name} (`{event.previous_guild_id}`)", inline=False)
    embed.add_field(name="New Guild", value=f"🏆 **{event.new_guild_name}** (`{event.new_guild_id}`)", inline=False)
    embed.set_footer(text="Ex-Member Guild Migration Tracking")
    return embed


def build_player_profile_embed(profile) -> discord.Embed:
    embed = discord.Embed(
        title=f"🔎 Player Profile & Guild Inspection",
        description=f"Detailed guild membership lookup for UID: `{profile.uid}`",
        color=0x3498DB
    )
    embed.set_author(name="Free Fire Player Tracker", icon_url=FREE_FIRE_ICON_URL)
    embed.add_field(name="Nickname", value=f"**{profile.nickname}**", inline=True)
    embed.add_field(name="Level", value=f"Lv. {profile.level}", inline=True)
    embed.add_field(name="Likes", value=f"❤️ {profile.likes:,}", inline=True)
    
    if profile.current_guild_name:
        guild_info = f"🏆 **{profile.current_guild_name}**\nID: `{profile.current_guild_id}`"
    else:
        guild_info = "❌ *Not in any guild (Guildless)*"
    embed.add_field(name="Current Guild", value=guild_info, inline=False)

    if profile.previous_guild_name and profile.previous_guild_id != profile.current_guild_id:
        embed.add_field(
            name="Previous Guild",
            value=f"{profile.previous_guild_name} (`{profile.previous_guild_id}`)",
            inline=False
        )

    embed.set_footer(text="Free Fire Player & Guild History Lookup")
    return embed


def build_last_matches_embed(uid: str, nickname: str, matches: list, br_points: int = 0, cs_points: int = 0) -> discord.Embed:
    embed = discord.Embed(
        title=f"🎮 Free Fire: Recent Match History",
        description=f"Match performance and rank session log for **{nickname}** (`{uid}`)",
        color=0xE67E22
    )
    embed.set_author(name="Free Fire Match Performance Tracker", icon_url=FREE_FIRE_ICON_URL)
    
    if br_points or cs_points:
        embed.add_field(name="Current Ranks", value=f"⭐ **BR Points**: {br_points:,} • ⚔️ **CS Score**: {cs_points}", inline=False)
        
    if not matches:
        embed.add_field(
            name="📊 Match Log Status",
            value=(
                "ℹ️ *No previous matches logged yet for this player.*\n"
                "• **Session Tracking Activated**: The bot has recorded this player's baseline rank points.\n"
                "• When they complete matches and points update, their matches will automatically be logged here!"
            ),
            inline=False
        )
    else:
        for idx, m in enumerate(matches[:10], start=1):
            val = f"**{m['result']}** ({m['points_delta']})\n📅 `{m['timestamp']}` • {m['details']}"
            embed.add_field(name=f"#{idx} • {m['mode']}", value=val, inline=False)
            
    embed.set_footer(text="Free Fire Real-Time Match Tracker • HWK X6")
    return embed
