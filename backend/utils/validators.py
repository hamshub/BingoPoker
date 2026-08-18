"""Validators - Input validation functions for BingoPoker.

Provides validation for user inputs, room configurations, and game state.
All validators return tuple (is_valid: bool, error_message: str | None).
"""

import re


class ValidationError:
    """Validation error messages and codes."""

    VALID = (True, None)

    EMAIL_INVALID = (False, "Email format is invalid")
    EMAIL_REQUIRED = (False, "Email is required")
    USERNAME_REQUIRED = (False, "Username is required")
    USERNAME_TOO_SHORT = (False, "Username must be at least 1 character")
    USERNAME_TOO_LONG = (False, "Username must be 50 characters or less")
    ROOM_NAME_REQUIRED = (False, "Room name is required")
    ROOM_NAME_TOO_SHORT = (False, "Room name must be at least 1 character")
    ROOM_NAME_TOO_LONG = (False, "Room name must be 100 characters or less")
    ROOM_ID_INVALID = (False, "Room ID format is invalid")
    ROOM_ID_REQUIRED = (False, "Room ID is required")
    GRID_INVALID = (False, "Grid must be 5x5 array of strings")
    POKER_VALUE_INVALID = (False, "Poker value must be one of: 0, 1, 2, 3, 5, 8, 13, 21, split")
    POKER_VALUE_REQUIRED = (False, "Poker value is required")


class Validators:
    """Input validation utility methods."""

    # Regex patterns
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    ROOM_ID_PATTERN = re.compile(r'^room-[a-zA-Z0-9]{8}$')

    # Constants
    VALID_POKER_VALUES = {'0', '1', '2', '3', '5', '8', '13', '21', 'split'}
    USERNAME_MIN_LENGTH = 1
    USERNAME_MAX_LENGTH = 50
    ROOM_NAME_MIN_LENGTH = 1
    ROOM_NAME_MAX_LENGTH = 100
    GRID_SIZE = 5

    @staticmethod
    def validate_email(email: str) -> tuple:
        """
        Validate email format.

        Args:
            email: Email address to validate

        Returns:
            (True, None) if valid, (False, error_message) if invalid
        """
        if not email:
            return ValidationError.EMAIL_REQUIRED
        if not isinstance(email, str):
            return ValidationError.EMAIL_INVALID
        if not Validators.EMAIL_PATTERN.match(email):
            return ValidationError.EMAIL_INVALID
        return ValidationError.VALID

    @staticmethod
    def validate_username(username: str) -> tuple:
        """
        Validate username length.

        Args:
            username: Username to validate

        Returns:
            (True, None) if valid, (False, error_message) if invalid
        """
        if not username:
            return ValidationError.USERNAME_REQUIRED
        if not isinstance(username, str):
            return ValidationError.USERNAME_REQUIRED
        if len(username) < Validators.USERNAME_MIN_LENGTH:
            return ValidationError.USERNAME_TOO_SHORT
        if len(username) > Validators.USERNAME_MAX_LENGTH:
            return ValidationError.USERNAME_TOO_LONG
        return ValidationError.VALID

    @staticmethod
    def validate_room_name(room_name: str) -> tuple:
        """
        Validate room name length.

        Args:
            room_name: Room name to validate

        Returns:
            (True, None) if valid, (False, error_message) if invalid
        """
        if not room_name:
            return ValidationError.ROOM_NAME_REQUIRED
        if not isinstance(room_name, str):
            return ValidationError.ROOM_NAME_REQUIRED
        if len(room_name) < Validators.ROOM_NAME_MIN_LENGTH:
            return ValidationError.ROOM_NAME_TOO_SHORT
        if len(room_name) > Validators.ROOM_NAME_MAX_LENGTH:
            return ValidationError.ROOM_NAME_TOO_LONG
        return ValidationError.VALID

    @staticmethod
    def validate_room_id(room_id: str) -> tuple:
        """
        Validate room ID format (room-XXXXXXXX).

        Args:
            room_id: Room ID to validate

        Returns:
            (True, None) if valid, (False, error_message) if invalid
        """
        if not room_id:
            return ValidationError.ROOM_ID_REQUIRED
        if not isinstance(room_id, str):
            return ValidationError.ROOM_ID_INVALID
        if not Validators.ROOM_ID_PATTERN.match(room_id):
            return ValidationError.ROOM_ID_INVALID
        return ValidationError.VALID

    @staticmethod
    def validate_grid(grid: list) -> tuple:
        """
        Validate 5x5 grid structure.

        Args:
            grid: 2D array of cell texts (should be 5x5)

        Returns:
            (True, None) if valid, (False, error_message) if invalid
        """
        if not isinstance(grid, list):
            return ValidationError.GRID_INVALID
        if len(grid) != Validators.GRID_SIZE:
            return ValidationError.GRID_INVALID
        for row in grid:
            if not isinstance(row, list) or len(row) != Validators.GRID_SIZE:
                return ValidationError.GRID_INVALID
            for cell in row:
                if not isinstance(cell, str):
                    return ValidationError.GRID_INVALID
        return ValidationError.VALID

    @staticmethod
    def validate_poker_value(value: str) -> tuple:
        """
        Validate poker value is one of allowed enum values.

        Args:
            value: Poker value to validate

        Returns:
            (True, None) if valid, (False, error_message) if invalid
        """
        if not value:
            return ValidationError.POKER_VALUE_REQUIRED
        if not isinstance(value, str):
            return ValidationError.POKER_VALUE_INVALID
        if value not in Validators.VALID_POKER_VALUES:
            return ValidationError.POKER_VALUE_INVALID
        return ValidationError.VALID
