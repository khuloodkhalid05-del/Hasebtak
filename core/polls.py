"""
core/polls.py
Pillar 3 — نبض المواطن (Citizen's Pulse)
Interactive anonymous polling engine tackling the Open Budget Survey Public Participation gap (35/100).
"""

import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional

POLL_BANK_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "poll_bank.json")
POLL_VOTES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "poll_votes.json")
SALT = "hasebtak_citizen_pulse_2026_salt"


class PollEngine:
    def __init__(self, bank_path: str = POLL_BANK_PATH, votes_path: str = POLL_VOTES_PATH):
        self.bank_path = bank_path
        self.votes_path = votes_path
        self._ensure_files()

    def _ensure_files(self):
        try:
            if not os.path.exists(self.votes_path):
                with open(self.votes_path, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _hash_user(self, user_channel_id: str) -> str:
        """One-way SHA-256 hash ensuring zero PII storage."""
        combined = f"{user_channel_id}:{SALT}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def get_active_poll(self) -> Optional[Dict[str, Any]]:
        """Returns the currently active weekly poll from the bank."""
        if not os.path.exists(self.bank_path):
            return None
        with open(self.bank_path, "r", encoding="utf-8") as f:
            polls = json.load(f)
            for poll in polls:
                if poll.get("is_active", False):
                    return poll
            return polls[0] if polls else None

    def get_poll_by_id(self, poll_id: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(self.bank_path):
            return None
        with open(self.bank_path, "r", encoding="utf-8") as f:
            polls = json.load(f)
            for poll in polls:
                if poll["id"] == poll_id:
                    return poll
        return None

    def record_vote(
        self,
        user_channel_id: str,
        poll_id: str,
        option_id: str,
        user_profile: Optional[str] = "مواطن"
    ) -> Dict[str, Any]:
        """
        Records an anonymous vote. Prevents duplicate votes per user per poll.
        """
        user_hash = self._hash_user(user_channel_id)
        
        votes = []
        if os.path.exists(self.votes_path):
            with open(self.votes_path, "r", encoding="utf-8") as f:
                try:
                    votes = json.load(f)
                except Exception:
                    votes = []

        # Check if already voted
        for vote in votes:
            if vote.get("poll_id") == poll_id and vote.get("user_hash") == user_hash:
                return {
                    "success": False,
                    "message": "شكراً لمشاركتك! لقد سجلت رأيك بالفعل في هذا الاستطلاع سابقاً 🗳️",
                    "already_voted": True
                }

        new_vote = {
            "poll_id": poll_id,
            "option_id": option_id,
            "user_hash": user_hash,
            "user_profile": user_profile or "مواطن",
            "timestamp": datetime.now().isoformat()
        }
        votes.append(new_vote)

        with open(self.votes_path, "w", encoding="utf-8") as f:
            json.dump(votes, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "message": "تم تسجيل صوتك بنجاح! صوتك بيوصل لصناع القرار في وزارة المالية 🇪🇬",
            "already_voted": False
        }

    def get_poll_stats(self, poll_id: str) -> Dict[str, Any]:
        """
        Aggregates anonymous statistics for a poll using SQLite for real-time consistency.
        """
        try:
            from core import database as db
            db_res = db.get_poll_results(poll_id)
            if "results" in db_res and db_res["total_votes"] > 0:
                options_stats = [
                    {
                        "id": r["option_id"],
                        "text": r["option_text"],
                        "votes": r["votes"],
                        "percentage": r["percentage"]
                    }
                    for r in db_res["results"]
                ]
                return {
                    "poll_id": db_res["poll_id"],
                    "question": db_res["question"],
                    "topic": "أولويات الإنفاق العام",
                    "total_votes": db_res["total_votes"],
                    "options": options_stats
                }
        except Exception:
            pass

        poll = self.get_poll_by_id(poll_id)
        if not poll:
            return {"total_votes": 0, "options": []}

        votes = []
        if os.path.exists(self.votes_path):
            with open(self.votes_path, "r", encoding="utf-8") as f:
                try:
                    votes = json.load(f)
                except Exception:
                    votes = []

        poll_votes = [v for v in votes if v.get("poll_id") == poll_id]
        total_votes = len(poll_votes)

        options_stats = []
        for opt in poll.get("options", []):
            opt_id = opt["id"]
            count = sum(1 for v in poll_votes if v.get("option_id") == opt_id)
            pct = round((count / total_votes * 100), 1) if total_votes > 0 else 0.0
            options_stats.append({
                "id": opt_id,
                "text": opt["text_ar"],
                "votes": count,
                "percentage": pct
            })

        return {
            "poll_id": poll_id,
            "question": poll.get("question_ar", ""),
            "topic": poll.get("topic", ""),
            "total_votes": total_votes,
            "options": options_stats
        }

