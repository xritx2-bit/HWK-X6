import asyncio
import aiohttp
import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from models import GuildMember, MemberState, GuildSnapshot

logger = logging.getLogger("FreeFireClient")

class BaseFreeFireClient(ABC):
    @abstractmethod
    async def get_guild_snapshot(self, guild_id: str) -> Optional[GuildSnapshot]:
        """Fetch the current full snapshot of the guild including members and activity logs."""
        pass

    @abstractmethod
    async def get_recent_guild_logs(self, guild_id: str) -> List[dict]:
        """Fetch recent guild events (approvals, joins, leaves, invites)."""
        pass


class FreeFireApiClient(BaseFreeFireClient):
    """
    Client that connects to an authenticated Free Fire API Gateway or Session Endpoint.
    
    IMPORTANT ARCHITECTURE NOTE:
    Free Fire uses encrypted Protocol Buffers over TCP/TLS and does not have an open public API.
    To monitor private guild activity (in-match statuses, guild approvals, invites), 
    the request must carry the authentication token (JWT / session token) of an alt account
    that is physically an Officer or Elder inside the target guild.
    """
    def __init__(self, gateway_url: str, access_token: str = "", account_uid: str = "", region: str = "IND", api_key: str = ""):
        self.gateway_url = gateway_url.rstrip("/")
        self.access_token = access_token
        self.account_uid = account_uid
        self.region = region
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {
                "User-Agent": "FreeFireGuildMonitor/1.0",
                "X-GARENA-REGION": self.region,
                "Content-Type": "application/json"
            }
            if self.api_key:
                headers["x-api-key"] = self.api_key
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def get_guild_snapshot(self, guild_id: str) -> Optional[GuildSnapshot]:
        session = await self._get_session()
        url = f"{self.gateway_url}/api/v1/guild/{guild_id}/members"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    members: List[GuildMember] = []
                    for m in data.get("members", []):
                        state = MemberState.from_game_status(m.get("online_status", 0), m.get("game_mode"))
                        members.append(GuildMember(
                            uid=str(m.get("uid", "")),
                            nickname=m.get("nickname", "Unknown"),
                            level=int(m.get("level", 1)),
                            role=m.get("role", "Member"),
                            state=state,
                            game_mode=m.get("game_mode"),
                            last_online_timestamp=m.get("last_online", int(time.time())),
                            guild_score=m.get("guild_score", 0)
                        ))
                    
                    return GuildSnapshot(
                        guild_id=guild_id,
                        guild_name=data.get("guild_name", "Free Fire Guild"),
                        guild_level=int(data.get("guild_level", 4)),
                        member_count=len(members),
                        max_members=int(data.get("max_members", 50)),
                        members=members,
                        recent_activity_logs=data.get("recent_logs", [])
                    )
                else:
                    logger.error(f"Error fetching guild snapshot: HTTP {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Exception connecting to Free Fire Gateway: {e}")
            return None

    async def get_recent_guild_logs(self, guild_id: str) -> List[dict]:
        session = await self._get_session()
        url = f"{self.gateway_url}/api/v1/guild/{guild_id}/activity_logs"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("logs", [])
                return []
        except Exception as e:
            logger.error(f"Exception fetching guild activity logs: {e}")
            return []

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


class FreeFireMockClient(BaseFreeFireClient):
    """
    Simulation client for local testing and demonstration.
    Allows running the bot immediately without requiring active Free Fire session tokens.
    Simulates dynamic player activity (playing CS/BR, entering lobby, invites, and approvals).
    """
    def __init__(self, guild_id: str = "772183921"):
        self.guild_id = guild_id
        self._step_counter = 0

        # Sample guild roster
        self.members: Dict[str, GuildMember] = {
            "10000001": GuildMember(uid="10000001", nickname="⚡THUNDER⚡", level=72, role="Leader", state=MemberState.ONLINE),
            "10000002": GuildMember(uid="10000002", nickname="亗_SHADOW_亗", level=68, role="Officer", state=MemberState.ONLINE),
            "10000003": GuildMember(uid="10000003", nickname="★VIPER★", level=65, role="Officer", state=MemberState.OFFLINE),
            "10000004": GuildMember(uid="10000004", nickname="Hunter_007", level=59, role="Member", state=MemberState.OFFLINE),
            "10000005": GuildMember(uid="10000005", nickname="NoobMaster99", level=54, role="Member", state=MemberState.OFFLINE),
            "10000006": GuildMember(uid="10000006", nickname="Phoenix_FF", level=61, role="Member", state=MemberState.OFFLINE),
        }
        self.logs: List[dict] = []
        self._log_id = 100

    async def get_guild_snapshot(self, guild_id: str) -> Optional[GuildSnapshot]:
        self._step_counter += 1
        
        # Simulate realistic gameplay changes every few cycles
        if self._step_counter == 2:
            # Hunter_007 comes online and starts playing Clash Squad
            m = self.members["10000004"]
            m.state = MemberState.PLAYING_CS
            m.game_mode = "Clash Squad Ranked"
            logger.info(f"[SIMULATION] {m.nickname} started playing Clash Squad Ranked")

        elif self._step_counter == 3:
            # 亗_SHADOW_亗 starts playing Battle Royale Ranked
            m = self.members["10000002"]
            m.state = MemberState.PLAYING_BR
            m.game_mode = "BR Ranked"
            logger.info(f"[SIMULATION] {m.nickname} entered Battle Royale Ranked")

            # Hunter_007 sends invite to a friend UID
            self._log_id += 1
            self.logs.append({
                "id": str(self._log_id),
                "type": "INVITE_SENT",
                "inviter_uid": "10000004",
                "inviter_name": "Hunter_007",
                "target_uid": "99887766",
                "target_name": "SniperGod_Op",
                "timestamp": int(time.time())
            })
            logger.info("[SIMULATION] Invite sent by Hunter_007 to UID 99887766")

        elif self._step_counter == 4:
            # An approval event happens: 亗_SHADOW_亗 approves new member "SniperGod_Op"
            self._log_id += 1
            self.logs.append({
                "id": str(self._log_id),
                "type": "JOIN_APPROVED",
                "applicant_uid": "99887766",
                "applicant_name": "SniperGod_Op",
                "approved_by_uid": "10000002",
                "approved_by_name": "亗_SHADOW_亗",
                "timestamp": int(time.time())
            })
            # Add member to guild roster
            self.members["99887766"] = GuildMember(
                uid="99887766",
                nickname="SniperGod_Op",
                level=62,
                role="Member",
                state=MemberState.ONLINE
            )
            logger.info("[SIMULATION] 亗_SHADOW_亗 approved SniperGod_Op into guild")

        elif self._step_counter == 5:
            # Hunter_007 finishes match and goes back to Lobby
            m = self.members["10000004"]
            m.state = MemberState.ONLINE
            m.game_mode = None
            logger.info(f"[SIMULATION] {m.nickname} returned to Lobby")

        return GuildSnapshot(
            guild_id=guild_id,
            guild_name="LEGENDARY_ELITE",
            guild_level=4,
            member_count=len(self.members),
            max_members=50,
            members=list(self.members.values()),
            recent_activity_logs=list(self.logs)
        )

    async def get_recent_guild_logs(self, guild_id: str) -> List[dict]:
        return list(self.logs)
