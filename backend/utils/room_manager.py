"""RoomManager - Manages room creation, configuration, and session state.

Handles room creation with 5x5 grid configurations, persistent storage in rooms.json,
and in-memory session state for active users and selections.
"""

import json
import os
import secrets
import string
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import aiofiles

from .color_palette import ColorPalette
from .validators import Validators


class RoomManager:
    """Manages room creation, loading, and session state."""

    def __init__(self, data_dir: str = "backend/data"):
        """
        Initialize RoomManager.

        Args:
            data_dir: Directory where rooms.json is stored
        """
        self.data_dir = data_dir
        self.rooms_file = os.path.join(data_dir, "rooms.json")
        self.rooms: Dict[str, Dict[str, Any]] = {}  # Persistent config
        self.sessions: Dict[str, Dict[str, Any]] = {}  # In-memory session state

    async def load(self) -> None:
        """
        Load room configurations from rooms.json into memory.

        Creates rooms.json if it doesn't exist.
        Session state starts empty.
        """
        try:
            if os.path.exists(self.rooms_file):
                async with aiofiles.open(self.rooms_file, "r") as f:
                    content = await f.read()
                    self.rooms = json.loads(content) if content else {}
            else:
                self.rooms = {}
                await self._save_to_disk()
        except Exception as e:
            print(f"Error loading rooms: {e}")
            self.rooms = {}

    async def create_room(
        self, room_name: str, grid: list, created_by: str
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Create a new room with 5x5 grid configuration.

        Generates room ID, validates inputs, persists config,
        and initializes empty session state.

        Args:
            room_name: Display name for the room
            grid: 5x5 array of cell text strings
            created_by: Email of user creating the room

        Returns:
            (success: bool, error: str | None, room_data: dict | None)
        """
        # Validate inputs
        is_valid, error = Validators.validate_room_name(room_name)
        if not is_valid:
            return (False, error, None)

        is_valid, error = Validators.validate_grid(grid)
        if not is_valid:
            return (False, error, None)

        # Generate unique room ID: room-XXXXXXXX (8 random alphanumeric)
        room_id = self._generate_room_id()

        # Create room configuration
        room_config = {
            "room_id": room_id,
            "name": room_name,
            "config": {"grid": grid},
            "created_at": datetime.utcnow().isoformat(),
            "created_by": created_by,
        }

        # Store config and persist
        self.rooms[room_id] = room_config
        await self._save_to_disk()

        # Initialize empty session state with a monotonic color counter
        self.sessions[room_id] = {
            "users": [],
            "bingo_selections": {},
            "poker_selections": {},
            "revealed": False,
            "color_counter": 0,
        }

        return (True, None, room_config)

    async def get_room(self, room_id: str) -> Optional[Dict[str, Any]]:
        """
        Get room configuration by ID.

        Args:
            room_id: Room identifier

        Returns:
            Room config dict or None if not found
        """
        return self.rooms.get(room_id)

    async def get_room_state(self, room_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current room state (config + session).

        Args:
            room_id: Room identifier

        Returns:
            Combined room config and session state, or None if not found
        """
        if room_id not in self.rooms:
            return None

        session = self.sessions.get(
            room_id,
            {
                "users": [],
                "bingo_selections": {},
                "poker_selections": {},
                "revealed": False,
            },
        )

        return {
            "config": self.rooms[room_id],
            "session": session,
        }

    async def add_user_to_session(self, room_id: str, user_email: str, user_data: dict) -> bool:
        """
        Add user to room session, assigning the next color in rolling order.

        Args:
            room_id: Room identifier
            user_email: User's email
            user_data: User profile dict {email, username}

        Returns:
            True if added, False if room not found or user already in room
        """
        if room_id not in self.sessions:
            if room_id not in self.rooms:
                return False
            self.sessions[room_id] = {
                "users": [],
                "bingo_selections": {},
                "poker_selections": {},
                "revealed": False,
                "color_counter": 0,
            }

        session = self.sessions[room_id]

        # Check if user already in session
        if user_email in [u["email"] for u in session["users"]]:
            return False

        # Migrate legacy sessions that predate color_counter
        if "color_counter" not in session:
            session["color_counter"] = len(session["users"])

        # Assign next color using monotonic counter so rejoining users never collide
        color = ColorPalette.get_color_by_index(session["color_counter"])
        session["color_counter"] += 1

        self.sessions[room_id]["users"].append({**user_data, "color": color})
        return True

    async def remove_user_from_session(self, room_id: str, user_email: str) -> bool:
        """
        Remove user from room session (they left the room).

        Cleans up selections and clears session if room becomes empty.

        Args:
            room_id: Room identifier
            user_email: User's email

        Returns:
            True if removed, False if room/user not found
        """
        if room_id not in self.sessions:
            return False

        session = self.sessions[room_id]

        # Remove user from users list
        initial_count = len(session["users"])
        session["users"] = [u for u in session["users"] if u["email"] != user_email]
        if len(session["users"]) == initial_count:
            return False  # User not found

        # Clean up user's selections
        session["bingo_selections"].pop(user_email, None)
        session["poker_selections"].pop(user_email, None)

        # Clean up empty room
        if len(session["users"]) == 0:
            del self.sessions[room_id]

        return True

    async def record_bingo_selection(
        self, room_id: str, user_email: str, cell_row: int, cell_col: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Record a user's bingo cell selection.

        Args:
            room_id: Room identifier
            user_email: User's email
            cell_row: Row index (0-4)
            cell_col: Column index (0-4)

        Returns:
            (success: bool, error: str | None)
        """
        if room_id not in self.sessions:
            return (False, "Room not found")

        session = self.sessions[room_id]

        # Validate cell coordinates
        if not (0 <= cell_row < 5 and 0 <= cell_col < 5):
            return (False, "Invalid cell coordinates")

        # Initialize user's selections if not present
        if user_email not in session["bingo_selections"]:
            session["bingo_selections"][user_email] = []

        # Toggle: remove if present, add if not
        cell = (cell_row, cell_col)
        user_cells = session["bingo_selections"][user_email]
        if cell in user_cells:
            user_cells.remove(cell)
        else:
            user_cells.append(cell)

        return (True, None)

    async def record_poker_selection(
        self, room_id: str, user_email: str, value: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Record a user's poker value selection (hidden until reveal).

        Args:
            room_id: Room identifier
            user_email: User's email
            value: Poker value ('0', '1', '2', '3', '5', '8', '13', '21', 'split')

        Returns:
            (success: bool, error: str | None)
        """
        if room_id not in self.sessions:
            return (False, "Room not found")

        # Validate value
        is_valid, error = Validators.validate_poker_value(value)
        if not is_valid:
            return (False, error)

        session = self.sessions[room_id]

        # Record selection (overwrites previous if exists)
        session["poker_selections"][user_email] = value

        return (True, None)

    async def reveal_round(self, room_id: str) -> Tuple[bool, Optional[str]]:
        """
        Reveal all poker selections for the room.

        Args:
            room_id: Room identifier

        Returns:
            (success: bool, error: str | None)
        """
        if room_id not in self.rooms:
            return (False, "Room not found")

        # Initialize session if no one has joined yet (edge case)
        if room_id not in self.sessions:
            self.sessions[room_id] = {
                "users": [],
                "bingo_selections": {},
                "poker_selections": {},
                "revealed": False,
                "color_counter": 0,
            }

        self.sessions[room_id]["revealed"] = True
        return (True, None)

    async def reset_round(self, room_id: str) -> Tuple[bool, Optional[str]]:
        """
        Reset selections for a new round.

        Clears bingo/poker selections and unreveals.

        Args:
            room_id: Room identifier

        Returns:
            (success: bool, error: str | None)
        """
        if room_id not in self.sessions:
            return (False, "Room not found")

        session = self.sessions[room_id]
        session["bingo_selections"] = {}
        session["poker_selections"] = {}
        session["revealed"] = False

        return (True, None)

    async def get_active_rooms(self) -> Dict[str, Dict[str, Any]]:
        """Get all persisted rooms regardless of whether anyone is currently in them."""
        return self.rooms.copy()

    async def _save_to_disk(self) -> None:
        """
        Persist room configurations to rooms.json.

        Called after room creation. Session state is ephemeral.
        """
        try:
            # Ensure directory exists
            os.makedirs(self.data_dir, exist_ok=True)

            # Write to file
            async with aiofiles.open(self.rooms_file, "w") as f:
                content = json.dumps(self.rooms, indent=2)
                await f.write(content)
        except Exception as e:
            print(f"Error saving rooms: {e}")

    @staticmethod
    def _generate_room_id() -> str:
        """
        Generate a unique room ID in format: room-XXXXXXXX

        Returns:
            Random room ID
        """
        chars = string.ascii_letters + string.digits
        random_part = "".join(secrets.choice(chars) for _ in range(8))
        return f"room-{random_part}"
