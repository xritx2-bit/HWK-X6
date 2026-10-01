import copy
import logging
from dataclasses import replace
from typing import Dict, List, Set, Tuple
from models import (
    GuildMember,
    MemberState,
    StatusChangeEvent,
    MemberJoinedEvent,
    MemberLeftEvent,
    InviteSentEvent,
    GuildSnapshot
)

logger = logging.getLogger("GuildTracker")

class GuildTracker:
    def __init__(self):
        # Known state of members mapped by UID
        self.known_members: Dict[str, GuildMember] = {}
        # Set of already processed activity log IDs to avoid duplicate alerts
        self.processed_log_ids: Set[str] = set()
        self.is_initialized: bool = False

    def process_snapshot(self, snapshot: GuildSnapshot) -> Tuple[
        List[StatusChangeEvent],
        List[MemberJoinedEvent],
        List[MemberLeftEvent],
        List[InviteSentEvent]
    ]:
        """
        Compare current snapshot with previous state and return newly detected events.
        """
        status_events: List[StatusChangeEvent] = []
        joined_events: List[MemberJoinedEvent] = []
        left_events: List[MemberLeftEvent] = []
        invite_events: List[InviteSentEvent] = []

        current_members: Dict[str, GuildMember] = {m.uid: m for m in snapshot.members}

        # 1. Process Activity Logs first (to have approval/invite details ready)
        pending_approvals: Dict[str, dict] = {}  # applicant_uid -> approval info
        for log in snapshot.recent_activity_logs:
            log_id = str(log.get("id", f"{log.get('type')}_{log.get('timestamp')}_{log.get('applicant_uid') or log.get('target_uid')}"))
            if log_id in self.processed_log_ids:
                continue

            self.processed_log_ids.add(log_id)

            log_type = log.get("type", "").upper()

            # Guild Join Approval Log
            if log_type in ("JOIN_APPROVED", "APPROVAL", "ACCEPT"):
                applicant_uid = str(log.get("applicant_uid", ""))
                pending_approvals[applicant_uid] = log

            # Guild Invitation Log
            elif log_type in ("INVITE_SENT", "INVITE", "MEMBER_INVITE"):
                if self.is_initialized:
                    invite_events.append(InviteSentEvent(
                        inviter_uid=str(log.get("inviter_uid", "Unknown")),
                        inviter_name=log.get("inviter_name", "Guild Member"),
                        target_uid=str(log.get("target_uid", "Unknown")),
                        target_name=log.get("target_name")
                    ))

        # First run: initialize known state without flooding notifications
        if not self.is_initialized:
            self.known_members = {uid: replace(m) for uid, m in current_members.items()}
            self.is_initialized = True
            logger.info(f"Initialized GuildTracker with {len(self.known_members)} members.")
            return [], [], [], []

        # 2. Check for New Members (Joined)
        for uid, member in current_members.items():
            if uid not in self.known_members:
                # Member is new! Check if we have approval record for who accepted them
                approval_info = pending_approvals.get(uid)
                approved_by_uid = None
                approved_by_name = None
                if approval_info:
                    approved_by_uid = approval_info.get("approved_by_uid")
                    approved_by_name = approval_info.get("approved_by_name")

                joined_events.append(MemberJoinedEvent(
                    uid=member.uid,
                    nickname=member.nickname,
                    approved_by_uid=approved_by_uid,
                    approved_by_name=approved_by_name
                ))

        # 3. Check for Members who Left or were Kicked
        for uid, member in self.known_members.items():
            if uid not in current_members:
                left_events.append(MemberLeftEvent(
                    uid=member.uid,
                    nickname=member.nickname
                ))

        # 4. Check for In-Game Status Changes (e.g. Started Playing BR/CS or returned to Lobby)
        for uid, current in current_members.items():
            if uid in self.known_members:
                previous = self.known_members[uid]
                if current.state != previous.state or current.game_mode != previous.game_mode:
                    status_events.append(StatusChangeEvent(
                        member=current,
                        old_state=previous.state,
                        new_state=current.state
                    ))

        # Update cache
        self.known_members = {uid: replace(m) for uid, m in current_members.items()}

        return status_events, joined_events, left_events, invite_events
