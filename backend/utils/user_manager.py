"""UserManager - Manages user registration and persistence.

Handles user registration, profile retrieval, and persistent storage
in users.json. Emails are never persisted in plain text: each user is
keyed by a random user ID and identified by an HMAC-SHA256 email digest.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import uuid
from typing import Optional, Dict, Any

import aiofiles

from .validators import Validators

logger = logging.getLogger(__name__)


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
        self.pepper_file = os.path.join(data_dir, ".email_pepper")
        self.users: Dict[str, Dict[str, Any]] = {}  # user_id -> profile
        self._by_email_hash: Dict[str, str] = {}  # email_hash -> user_id
        self._pepper: bytes = b""

    async def load(self) -> None:
        """
        Load users from users.json into memory.

        Creates users.json if it doesn't exist and migrates any legacy
        email-keyed records to the hashed/UID format.
        """
        self._pepper = self._load_or_create_pepper()

        try:
            if os.path.exists(self.users_file):
                async with aiofiles.open(self.users_file, "r") as f:
                    content = await f.read()
                    self.users = json.loads(content) if content else {}
            else:
                self.users = {}
                await self._save_to_disk()
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            self.users = {}

        migrated = self._migrate_legacy_records()
        self._rebuild_index()
        if migrated:
            await self._save_to_disk()
            logger.info(f"Migrated {migrated} legacy user record(s) to hashed storage")

    def hash_email(self, email: str) -> str:
        """Return the stable, non-reversible digest used to identify an email."""
        normalized = (email or "").strip().lower().encode("utf-8")
        return hmac.new(self._pepper, normalized, hashlib.sha256).hexdigest()

    def resolve_user_id(self, email: str) -> Optional[str]:
        """Return the random user ID for an email, or None if unknown."""
        return self._by_email_hash.get(self.hash_email(email))

    async def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile by email.

        Args:
            email: User email address

        Returns:
            User profile dict (with the email echoed back) or None if not found
        """
        user_id = self.resolve_user_id(email)
        if not user_id:
            return None
        return self._public_profile(user_id, email)

    async def register_user(
        self, email: str, username: str, role: str = "worker"
    ) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Register a new user or get existing user.

        Validates email and username, generates a random user ID, and persists
        only the hashed email to users.json.

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
        existing_id = self.resolve_user_id(email)
        if existing_id:
            return (True, None, self._public_profile(existing_id, email))

        if role not in ("observer", "worker"):
            role = "worker"

        user_id = uuid.uuid4().hex
        email_hash = self.hash_email(email)

        # Stored profile — color is assigned per room session, not stored here
        self.users[user_id] = {
            "user_id": user_id,
            "email_hash": email_hash,
            "username": username,
            "role": role,
        }
        self._by_email_hash[email_hash] = user_id
        await self._save_to_disk()

        return (True, None, self._public_profile(user_id, email))

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

        user_id = self.resolve_user_id(email)
        if not user_id:
            return (False, "User not found")

        # Update and persist
        self.users[user_id]["username"] = new_username
        await self._save_to_disk()

        return (True, None)

    async def update_role(self, email: str, new_role: str) -> tuple[bool, Optional[str]]:
        """
        Update user's role.

        Args:
            email: User email address
            new_role: New role ('worker' or 'observer')

        Returns:
            (success: bool, error: str | None)
        """
        # Validate role
        if new_role not in ("worker", "observer"):
            return (False, "Role must be 'worker' or 'observer'")

        user_id = self.resolve_user_id(email)
        if not user_id:
            return (False, "User not found")

        # Update and persist
        self.users[user_id]["role"] = new_role
        await self._save_to_disk()

        return (True, None)

    async def user_exists(self, email: str) -> bool:
        """
        Check if user is registered.

        Args:
            email: User email address

        Returns:
            True if user exists, False otherwise
        """
        return self.resolve_user_id(email) is not None

    def _public_profile(self, user_id: str, email: Optional[str] = None) -> Dict[str, Any]:
        """Build an API-facing profile without exposing the stored email digest."""
        stored = self.users[user_id]
        profile = {
            "user_id": user_id,
            "username": stored.get("username"),
            "role": stored.get("role", "worker"),
        }
        if email:
            profile["email"] = email
        return profile

    def _rebuild_index(self) -> None:
        """Rebuild the email-hash lookup index from stored records."""
        self._by_email_hash = {
            record["email_hash"]: user_id
            for user_id, record in self.users.items()
            if record.get("email_hash")
        }

    def _migrate_legacy_records(self) -> int:
        """Convert email-keyed records with plain emails to hashed/UID records."""
        legacy_keys = [
            key for key, record in self.users.items()
            if "email" in record or not record.get("email_hash")
        ]
        if not legacy_keys:
            return 0

        for key in legacy_keys:
            record = self.users.pop(key)
            email = record.get("email") or key
            user_id = record.get("user_id") or uuid.uuid4().hex
            self.users[user_id] = {
                "user_id": user_id,
                "email_hash": self.hash_email(email),
                "username": record.get("username", ""),
                "role": record.get("role", "worker"),
            }
        return len(legacy_keys)

    def _load_or_create_pepper(self) -> bytes:
        """Load the HMAC pepper, generating and storing one on first run."""
        env_pepper = os.getenv("EMAIL_HASH_PEPPER")
        if env_pepper:
            return env_pepper.encode("utf-8")

        try:
            os.makedirs(self.data_dir, exist_ok=True)
            if os.path.exists(self.pepper_file):
                with open(self.pepper_file, "r") as f:
                    stored = f.read().strip()
                if stored:
                    return stored.encode("utf-8")

            pepper = secrets.token_hex(32)
            with open(self.pepper_file, "w") as f:
                f.write(pepper)
            logger.info("Generated new email hashing pepper")
            return pepper.encode("utf-8")
        except Exception as e:
            logger.error(f"Error accessing email pepper file: {e}")
            raise

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
            logger.error(f"Error saving users: {e}")
