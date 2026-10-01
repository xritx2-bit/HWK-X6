import json
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger("ChannelManager")

CHANNELS_FILE = os.path.join(os.path.dirname(__file__), "channels.json")

class ChannelManager:
    """Manages dedicated channel IDs for different event types."""
    def __init__(self, default_channel_id: int = 0):
        self.default_channel_id = default_channel_id
        self.channels: Dict[str, int] = {
            "playing": 0,    # In-game match status updates (CS, BR, Lobby)
            "invites": 0,    # Guild invitations sent to friends
            "joins": 0,      # Guild joins & approval acceptances
            "leaves": 0,     # Member leaves, kicks, and new guild tracking
            "default": default_channel_id
        }
        self.load()

    def load(self):
        if os.path.exists(CHANNELS_FILE):
            try:
                with open(CHANNELS_FILE, "r") as f:
                    data = json.load(f)
                    self.channels.update(data)
                logger.info(f"Loaded channel routing: {self.channels}")
            except Exception as e:
                logger.error(f"Failed to load channels.json: {e}")

    def save(self):
        try:
            with open(CHANNELS_FILE, "w") as f:
                json.dump(self.channels, f, indent=2)
            logger.info("Saved channel routing configuration.")
        except Exception as e:
            logger.error(f"Failed to save channels.json: {e}")

    def set_channel(self, category: str, channel_id: int) -> bool:
        category = category.lower().strip()
        if category in self.channels or category in ("status", "approval", "leave", "invite"):
            # Normalize names
            if category == "status":
                category = "playing"
            elif category == "approval":
                category = "joins"
            elif category == "leave":
                category = "leaves"
            elif category == "invite":
                category = "invites"

            self.channels[category] = channel_id
            self.save()
            return True
        return False

    def get_channel_id(self, category: str) -> int:
        cat_id = self.channels.get(category, 0)
        if cat_id and cat_id > 0:
            return cat_id
        # Fall back to default
        return self.channels.get("default", self.default_channel_id)
