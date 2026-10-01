from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from datetime import datetime

class MemberState(Enum):
    OFFLINE = "Offline"
    ONLINE = "Online (Lobby)"
    PLAYING_BR = "In Match (Battle Royale)"
    PLAYING_CS = "In Match (Clash Squad)"
    PLAYING_LONE_WOLF = "In Match (Lone Wolf)"
    PLAYING_CUSTOM = "In Match (Custom Room)"
    PLAYING_OTHER = "In Match"

    @classmethod
    def from_game_status(cls, status_code: int, game_mode: Optional[str] = None) -> "MemberState":
        # Free Fire internal status code mapping:
        # 0: Offline, 1: Online/Lobby, 2: In Team/Squad, 3: In Match
        if status_code == 0:
            return cls.OFFLINE
        elif status_code in (1, 2):
            return cls.ONLINE
        elif status_code == 3:
            if not game_mode:
                return cls.PLAYING_OTHER
            gm = game_mode.lower()
            if "clash" in gm or "cs" in gm:
                return cls.PLAYING_CS
            elif "lone" in gm:
                return cls.PLAYING_LONE_WOLF
            elif "custom" in gm:
                return cls.PLAYING_CUSTOM
            elif "br" in gm or "battle" in gm or "ranked" in gm:
                return cls.PLAYING_BR
            return cls.PLAYING_OTHER
        return cls.OFFLINE

@dataclass
class GuildMember:
    uid: str
    nickname: str
    level: int
    role: str  # Leader, Officer, Elder, Member
    state: MemberState = MemberState.OFFLINE
    game_mode: Optional[str] = None
    last_online_timestamp: int = 0
    guild_score: int = 0

@dataclass
class StatusChangeEvent:
    member: GuildMember
    old_state: MemberState
    new_state: MemberState
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class MemberJoinedEvent:
    uid: str
    nickname: str
    approved_by_uid: Optional[str] = None
    approved_by_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class MemberLeftEvent:
    uid: str
    nickname: str
    kicked_by_uid: Optional[str] = None
    kicked_by_name: Optional[str] = None
    is_kick: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class InviteSentEvent:
    inviter_uid: str
    inviter_name: str
    target_uid: str
    target_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class GuildSnapshot:
    guild_id: str
    guild_name: str
    guild_level: int
    member_count: int
    max_members: int
    members: List[GuildMember] = field(default_factory=list)
    recent_activity_logs: List[dict] = field(default_factory=list)
