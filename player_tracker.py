import json
import os
import time
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger("PlayerTracker")

DEPARTURES_FILE = os.path.join(os.path.dirname(__file__), "departures.json")

@dataclass
class PlayerProfile:
    uid: str
    nickname: str
    level: int = 1
    likes: int = 0
    current_guild_id: Optional[str] = None
    current_guild_name: Optional[str] = None
    previous_guild_id: Optional[str] = None
    previous_guild_name: Optional[str] = None
    last_updated: int = 0

@dataclass
class ExMemberNewGuildEvent:
    uid: str
    nickname: str
    previous_guild_id: str
    previous_guild_name: str
    new_guild_id: str
    new_guild_name: str
    timestamp: datetime

class PlayerTracker:
    """
    Tracks departed members and monitors which new guild they join after leaving.
    Also provides on-demand lookup for any player UID.
    """
    def __init__(self, my_guild_id: str, my_guild_name: str = "HWK X6"):
        self.my_guild_id = my_guild_id
        self.my_guild_name = my_guild_name
        self.departed_members: Dict[str, dict] = {}
        self.load_departures()

    def load_departures(self):
        if os.path.exists(DEPARTURES_FILE):
            try:
                with open(DEPARTURES_FILE, "r") as f:
                    self.departed_members = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load departures.json: {e}")

    def save_departures(self):
        try:
            with open(DEPARTURES_FILE, "w") as f:
                json.dump(self.departed_members, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save departures.json: {e}")

    def record_departure(self, uid: str, nickname: str):
        """Record that a member has left our guild so we can monitor if they join another guild."""
        self.departed_members[uid] = {
            "uid": uid,
            "nickname": nickname,
            "left_guild_id": self.my_guild_id,
            "left_guild_name": self.my_guild_name,
            "left_timestamp": int(time.time()),
            "new_guild_detected": False,
            "current_guild_id": None,
            "current_guild_name": None
        }
        self.save_departures()
        logger.info(f"Recorded departure of member {nickname} (UID: {uid}) for guild tracking.")

    async def lookup_player(self, uid: str) -> Optional[PlayerProfile]:
        """
        Query player profile to inspect current guild status.
        Works in both mock/simulation mode and live API mode.
        """
        # If this UID is in our departed registry, check its status
        if uid in self.departed_members:
            dep = self.departed_members[uid]
            return PlayerProfile(
                uid=uid,
                nickname=dep.get("nickname", "Player"),
                level=65,
                likes=1250,
                current_guild_id=dep.get("current_guild_id"),
                current_guild_name=dep.get("current_guild_name"),
                previous_guild_id=dep.get("left_guild_id"),
                previous_guild_name=dep.get("left_guild_name"),
                last_updated=int(time.time())
            )

        # Try live query via HL Gaming or other gateway if configured
        from config import config
        if config.FF_API_GATEWAY_URL and config.FF_API_KEY:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    if "hlgamingofficial.com" in config.FF_API_GATEWAY_URL:
                        url = f"{config.FF_API_GATEWAY_URL.rstrip('/')}/main/games/freefire/account/api?sectionName=AllData&PlayerUid={uid}&region={config.FF_REGION.lower()}&useruid={config.FF_USER_UID}&api={config.FF_API_KEY}"
                        headers = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip, deflate"}
                    else:
                        url = f"{config.FF_API_GATEWAY_URL.rstrip('/')}/info?region={config.FF_REGION.lower()}&uid={uid}"
                        headers = {"x-api-key": config.FF_API_KEY, "Accept-Encoding": "gzip, deflate"}

                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if "hlgamingofficial.com" in config.FF_API_GATEWAY_URL:
                                res = data.get("result") or {}
                                acc = res.get("AccountInfo") or {}
                                guild = res.get("GuildInfo") or {}
                                likes_val = acc.get("AccountLikes")
                                likes_num = int(likes_val) if isinstance(likes_val, int) or (isinstance(likes_val, str) and likes_val.isdigit()) else 0
                                return PlayerProfile(
                                    uid=uid,
                                    nickname=acc.get("AccountName") or f"Player ({uid})",
                                    level=int(acc.get("AccountLevel") or 1),
                                    likes=likes_num,
                                    current_guild_id=str(guild.get("GuildID")) if guild.get("GuildID") else None,
                                    current_guild_name=guild.get("GuildName") if guild.get("GuildName") else None,
                                    previous_guild_id=self.my_guild_id,
                                    previous_guild_name=self.my_guild_name,
                                    last_updated=int(time.time())
                                )
                            else:
                                b = data.get("basicInfo") or {}
                                c = data.get("clanBasicInfo") or {}
                                return PlayerProfile(
                                    uid=uid,
                                    nickname=b.get("nickname") or f"Player ({uid})",
                                    level=int(b.get("level") or 1),
                                    likes=int(b.get("liked") or 0),
                                    current_guild_id=str(c.get("clanId")) if c.get("clanId") else None,
                                    current_guild_name=c.get("clanName") if c.get("clanName") else None,
                                    previous_guild_id=self.my_guild_id,
                                    previous_guild_name=self.my_guild_name,
                                    last_updated=int(time.time())
                                )
            except Exception as e:
                logger.warning(f"Live player lookup failed for UID {uid}: {e}")

        # Default Profile if not in departed registry and no live session yet
        return PlayerProfile(
            uid=uid,
            nickname=f"Player ({uid})",
            level=0,
            likes=0,
            current_guild_id=None,
            current_guild_name=None,
            previous_guild_id=self.my_guild_id,
            previous_guild_name=self.my_guild_name,
            last_updated=int(time.time())
        )

    def check_for_new_guilds(self) -> list:
        """
        Check all departed members to see if any have recently joined a new guild.
        """
        events = []
        for uid, data in list(self.departed_members.items()):
            if not data.get("new_guild_detected") and data.get("current_guild_id"):
                # Player has now joined a new guild!
                events.append(ExMemberNewGuildEvent(
                    uid=uid,
                    nickname=data.get("nickname", "Unknown"),
                    previous_guild_id=data.get("left_guild_id", self.my_guild_id),
                    previous_guild_name=data.get("left_guild_name", self.my_guild_name),
                    new_guild_id=data.get("current_guild_id", ""),
                    new_guild_name=data.get("current_guild_name", "Unknown Guild"),
                    timestamp=datetime.utcnow()
                ))
                data["new_guild_detected"] = True
        if events:
            self.save_departures()
        return events
