import asyncio
import aiohttp
import logging
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
    Real client that connects to an authenticated Free Fire API Gateway or Session Endpoint.
    Connects to Garena servers for real guild member data, live matches, approvals, and invites.
    """
    def __init__(self, gateway_url: str = "", access_token: str = "", account_uid: str = "", region: str = "IND", api_key: str = ""):
        self.gateway_url = gateway_url.rstrip("/") if gateway_url else ""
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
        # If no real gateway or token is connected yet, return a clean state without any fake players
        if not self.gateway_url:
            return GuildSnapshot(
                guild_id=guild_id,
                guild_name="HWK X6",
                guild_level=1,
                member_count=0,
                max_members=50,
                members=[],
                recent_activity_logs=[]
            )

        session = await self._get_session()
        
        # Support for Free Fire Community API Hub (developers.freefirecommunity.com)
        if "freefirecommunity.com" in self.gateway_url:
            url = f"{self.gateway_url}/info?region={self.region.lower()}&uid={self.account_uid}"
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        clan_info = data.get("clanBasicInfo") or {}
                        basic_info = data.get("basicInfo") or {}
                        
                        clan_name = clan_info.get("clanName") or "HWK X6"
                        clan_id = str(clan_info.get("clanId") or guild_id)
                        clan_lvl = int(clan_info.get("clanLevel") or 4)
                        member_num = int(clan_info.get("memberNum") or 1)
                        
                        # Add bot player as member
                        members = [
                            GuildMember(
                                uid=str(self.account_uid),
                                nickname=basic_info.get("nickname") or "HWK Member",
                                level=int(basic_info.get("level") or 1),
                                role="Officer",
                                state=MemberState.ONLINE,
                                last_online_timestamp=int(time.time()),
                                guild_score=0
                            )
                        ]
                        
                        return GuildSnapshot(
                            guild_id=clan_id,
                            guild_name=clan_name,
                            guild_level=clan_lvl,
                            member_count=member_num,
                            max_members=50,
                            members=members,
                            recent_activity_logs=[]
                        )
                    else:
                        logger.warning(f"Free Fire API Hub returned HTTP {resp.status}")
                        return None
            except Exception as e:
                logger.error(f"Cannot connect to Free Fire API Hub: {e}")
                return None

        # Standard custom REST Gateway endpoint
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
                        guild_name=data.get("guild_name", "HWK X6"),
                        guild_level=int(data.get("guild_level", 4)),
                        member_count=len(members),
                        max_members=int(data.get("max_members", 50)),
                        members=members,
                        recent_activity_logs=data.get("recent_logs", [])
                    )
                else:
                    logger.warning(f"Free Fire Gateway returned HTTP {resp.status} for guild {guild_id}")
                    return None
        except Exception as e:
            logger.error(f"Cannot connect to Free Fire Gateway: {e}")
            return None

    async def get_recent_guild_logs(self, guild_id: str) -> List[dict]:
        if not self.gateway_url:
            return []

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
