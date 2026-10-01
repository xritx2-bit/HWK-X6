import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Discord settings
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    DISCORD_CHANNEL_ID: int = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
    DISCORD_WEBHOOK_URL: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL", "")

    # Free Fire settings
    FF_REGION: str = os.getenv("FF_REGION", "IND")  # e.g., IND, BR, US, SG, EU
    FF_GUILD_ID: str = os.getenv("FF_GUILD_ID", "")
    FF_BOT_UID: str = os.getenv("FF_BOT_UID", "")  # Alt account UID in the guild
    FF_ACCESS_TOKEN: str = os.getenv("FF_ACCESS_TOKEN", "")  # Alt account session token
    FF_API_GATEWAY_URL: str = os.getenv("FF_API_GATEWAY_URL", "")  # Optional proxy / API gateway URL
    FF_API_KEY: str = os.getenv("FF_API_KEY", "")  # API Key for third-party Free Fire API provider

    # Polling & Mode settings
    POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
    MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() in ("true", "1", "yes")

config = Config()
