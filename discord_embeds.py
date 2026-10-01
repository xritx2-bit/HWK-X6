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
