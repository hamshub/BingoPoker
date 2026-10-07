"""AnalyticsManager - Lightweight usage statistics.

Keeps per-day aggregate counters in analytics.json. No emails or usernames are
stored; the random user IDs of the current day are held only to count unique
active users and are reduced to a number once the day is over.
"""

import json
import logging
import os
from datetime import date
from typing import Any, Callable, Dict, Iterable, Optional

import aiofiles

from .file_io import write_json_atomic

logger = logging.getLogger(__name__)


class AnalyticsManager:
    """Records and summarizes daily usage counters."""

    def __init__(self, data_dir: str = "backend/data", today: Optional[Callable[[], date]] = None):
        """
        Initialize AnalyticsManager.

        Args:
            data_dir: Directory where analytics.json is stored
            today: Date provider, injectable for tests
        """
        self.analytics_file = os.path.join(data_dir, "analytics.json")
        self.days: Dict[str, Dict[str, Any]] = {}
        self._today = today or date.today

    async def load(self) -> None:
        """Load analytics.json, starting empty if it is missing or unreadable."""
        try:
            if os.path.exists(self.analytics_file):
                async with aiofiles.open(self.analytics_file, "r", encoding="utf-8") as f:
                    content = await f.read()
                self.days = (json.loads(content) if content else {}).get("days", {})
        except Exception as e:
            logger.error(f"Error loading analytics: {e}")
            self.days = {}

    async def record_room_created(self) -> None:
        """Count a newly created room."""
        self._day()["rooms_created"] += 1
        await self._save()

    async def record_join(self, user_id: Optional[str], room_size: int) -> None:
        """
        Count a room join and track the day's unique users.

        Args:
            user_id: Random user ID of the joining user
            room_size: Number of participants in the room after the join
        """
        day = self._day()
        day["joins"] += 1
        day["peak_room_size"] = max(day["peak_room_size"], room_size)
        if user_id and user_id not in day["user_ids"]:
            day["user_ids"].append(user_id)
            day["active_users"] = len(day["user_ids"])
        await self._save()

    async def record_reveal(self, votes: Iterable[str], participants: int, auto: bool) -> None:
        """
        Count a revealed round and its vote distribution.

        Args:
            votes: Poker values cast in the round
            participants: Number of participants when the round was revealed
            auto: Whether auto-reveal triggered it
        """
        day = self._day()
        day["rounds_revealed"] += 1
        day["participants_in_rounds"] += participants
        if auto:
            day["auto_reveals"] += 1
        for value in votes:
            day["votes"][value] = day["votes"].get(value, 0) + 1
        await self._save()

    def get_summary(self) -> Dict[str, Any]:
        """
        Aggregate all recorded days.

        Returns:
            Dict with per-day rows (newest first), all-time totals, and the vote distribution
        """
        totals = {
            "rooms_created": 0, "joins": 0, "rounds_revealed": 0,
            "auto_reveals": 0, "participants_in_rounds": 0, "votes_cast": 0,
        }
        vote_distribution: Dict[str, int] = {}
        rows = []
        for day_key in sorted(self.days, reverse=True):
            day = self.days[day_key]
            for key in ("rooms_created", "joins", "rounds_revealed", "auto_reveals", "participants_in_rounds"):
                totals[key] += day.get(key, 0)
            day_votes = sum(day.get("votes", {}).values())
            totals["votes_cast"] += day_votes
            for value, count in day.get("votes", {}).items():
                vote_distribution[value] = vote_distribution.get(value, 0) + count
            rows.append({
                "date": day_key,
                "active_users": day.get("active_users", 0),
                "joins": day.get("joins", 0),
                "rooms_created": day.get("rooms_created", 0),
                "rounds_revealed": day.get("rounds_revealed", 0),
                "votes_cast": day_votes,
                "peak_room_size": day.get("peak_room_size", 0),
            })
        return {
            "days": rows,
            "totals": totals,
            "vote_distribution": vote_distribution,
            "days_active": len(rows),
        }

    def _day(self) -> Dict[str, Any]:
        """Return today's counters, compacting earlier days' user IDs into counts."""
        key = self._today().isoformat()
        if key not in self.days:
            # A new day started: earlier user ID lists are no longer needed
            for day in self.days.values():
                day.pop("user_ids", None)
            self.days[key] = {
                "rooms_created": 0,
                "joins": 0,
                "active_users": 0,
                "peak_room_size": 0,
                "rounds_revealed": 0,
                "auto_reveals": 0,
                "participants_in_rounds": 0,
                "votes": {},
                "user_ids": [],
            }
        day = self.days[key]
        day.setdefault("user_ids", [])
        return day

    async def _save(self) -> None:
        try:
            await write_json_atomic(self.analytics_file, {"days": self.days})
        except Exception as e:
            logger.error(f"Error saving analytics: {e}")
