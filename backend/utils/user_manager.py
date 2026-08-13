"""UserManager - Manages user registration and persistence.

Handles user registration, profile retrieval, and persistent storage
in users.json. Integrates with ColorPalette for color assignment.
"""

import json
import os
from typing import Optional, Dict, Any

import aiofiles

from .validators import Validators


class UserManager:
    """Manages user registration, profiles, and persistence."""

    def __init__(self, data_dir: str = "backend/data"):
        """
        Initialize UserManager.

        Args:
            data_dir: Directory where users.json is stored
        """
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, "users.json")
        self.users: Dict[str, Dict[str, Any]] = {}

    async def load(self) -> None:
        """
        Load users from users.json into memory.

        Creates users.json if it doesn't exist.
        """
        try:
            if os.path.exists(self.users_file):
                async with aiofiles.open(self.users_file, "r") as f:
                    content = await f.read()
                    self.users = json.loads(content) if content else {}
            else:
                self.users = {}
                await self._save_to_disk()
        except Exception as e:
            print(f"Error loading users: {e}")
            self.users = {}

    async def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile by email.

        Args:
            email: User email address

        Returns:
            User profile dict or None if not found
        """
        return self.users.get(email)

    async def register_user(
        self, email: str, username: str, role: str = "worker"
    ) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Register a new user or get existing user.

        Validates email and username, assigns color if new user,
        and persists to users.json.

        Args:
            email: User email address
            username: Display username
            role: 'observer' (PO) or 'worker' (developer/tester)

        Returns:
            (success: bool, error: str | None, user_profile: dict | None)
        """
        # Validate inputs
        is_valid, error = Validators.validate_email(email)
        if not is_valid:
            return (False, error, None)

        is_valid, error = Validators.validate_username(username)
        if not is_valid:
            return (False, error, None)

        # Check if user already exists
        if email in self.users:
            return (True, None, self.users[email])

        if role not in ("observer", "worker"):
            role = "worker"

        # Create user profile — color is assigned per room session, not stored here
        user_profile = {
            "email": email,
            "username": username,
            "role": role,
        }

        # Store in memory and persist
        self.users[email] = user_profile
        await self._save_to_disk()

        return (True, None, user_profile)

    async def update_username(self, email: str, new_username: str) -> tuple[bool, Optional[str]]:
        """
        Update user's username.

        Args:
            email: User email address
            new_username: New display username

        Returns:
            (success: bool, error: str | None)
        """
        # Validate
        is_valid, error = Validators.validate_username(new_username)
        if not is_valid:
            return (False, error)

        # Check user exists
        if email not in self.users:
            return (False, "User not found")

        # Update and persist
        self.users[email]["username"] = new_username
        await self._save_to_disk()

        return (True, None)

    async def get_all_users(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all registered users.

        Returns:
            Dictionary of email -> user profile
        """
        return self.users.copy()

    async def user_exists(self, email: str) -> bool:
        """
        Check if user is registered.

        Args:
            email: User email address

        Returns:
            True if user exists, False otherwise
        """
        return email in self.users

    async def _save_to_disk(self) -> None:
        """
        Persist users to users.json.

        Called after registration or profile updates.
        """
        try:
            # Ensure directory exists
            os.makedirs(self.data_dir, exist_ok=True)

            # Write to file
            async with aiofiles.open(self.users_file, "w") as f:
                content = json.dumps(self.users, indent=2)
                await f.write(content)
        except Exception as e:
            print(f"Error saving users: {e}")
