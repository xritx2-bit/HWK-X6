import json
import os
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime

MATCHES_FILE = os.path.join(os.path.dirname(__file__), "match_history.json")

@dataclass
class MatchRecord:
    mode: str
    result: str  # "VICTORY", "DEFEAT", "BOOYAH"
    points_delta: str  # e.g. "+34 Pts", "-12 Pts"
    timestamp: str
    details: str

class MatchTracker:
    """
    Tracks and records match history sessions for Free Fire players by monitoring
    Rank Points, EXP deltas, and match outcomes.
    """
    def __init__(self):
        self.history: Dict[str, List[dict]] = {}
        self.snapshots: Dict[str, dict] = {}
        self.load()

    def load(self):
        if os.path.exists(MATCHES_FILE):
            try:
                with open(MATCHES_FILE, "r") as f:
                    data = json.load(f)
                    self.history = data.get("history", {})
                    self.snapshots = data.get("snapshots", {})
            except Exception:
                self.history = {}
                self.snapshots = {}

    def save(self):
        try:
            with open(MATCHES_FILE, "w") as f:
                json.dump({
                    "history": self.history,
                    "snapshots": self.snapshots
                }, f, indent=2)
        except Exception:
            pass

    def record_snapshot(self, uid: str, nickname: str, br_points: int, cs_points: int, exp: int) -> Optional[MatchRecord]:
        """
        Compare player stats against previous snapshot and register a new match if points changed.
        """
        now_str = datetime.now().strftime("%d %b %I:%M %p")
        last = self.snapshots.get(uid)

        new_record = None
        if last:
            old_br = last.get("br_points", br_points)
            old_cs = last.get("cs_points", cs_points)
            old_exp = last.get("exp", exp)

            # Check Clash Squad point changes
            if cs_points != old_cs:
                diff = cs_points - old_cs
                res = "VICTORY 🏆" if diff > 0 else "DEFEAT 💀"
                delta_str = f"+{diff} Stars" if diff > 0 else f"{diff} Stars"
                new_record = MatchRecord(
                    mode="Clash Squad (Ranked)",
                    result=res,
                    points_delta=delta_str,
                    timestamp=now_str,
                    details=f"CS Points: {cs_points}"
                )
            # Check Battle Royale point changes
            elif br_points != old_br:
                diff = br_points - old_br
                res = "BOOYAH #1 👑" if diff >= 30 else ("VICTORY 🏆" if diff > 0 else "DEFEAT 💀")
                delta_str = f"+{diff} Pts" if diff > 0 else f"{diff} Pts"
                new_record = MatchRecord(
                    mode="Battle Royale (Ranked)",
                    result=res,
                    points_delta=delta_str,
                    timestamp=now_str,
                    details=f"BR Rank Points: {br_points}"
                )
            # Check EXP change (Unranked match)
            elif exp > old_exp:
                exp_diff = exp - old_exp
                new_record = MatchRecord(
                    mode="Match Completed (Classic / Custom)",
                    result="COMPLETED ✅",
                    points_delta=f"+{exp_diff} EXP",
                    timestamp=now_str,
                    details=f"Total EXP: {exp}"
                )

        # Update latest snapshot
        self.snapshots[uid] = {
            "nickname": nickname,
            "br_points": br_points,
            "cs_points": cs_points,
            "exp": exp,
            "last_updated": int(time.time())
        }

        if new_record:
            if uid not in self.history:
                self.history[uid] = []
            self.history[uid].insert(0, asdict(new_record))
            # Keep up to 20 matches per player
            self.history[uid] = self.history[uid][:20]
            self.save()

        return new_record

    def get_last_matches(self, uid: str, limit: int = 10) -> List[dict]:
        """Return the last recorded matches for a given UID."""
        return self.history.get(uid, [])[:limit]

match_tracker = MatchTracker()
