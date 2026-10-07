"""Tests for input validators."""

import pytest

from utils.validators import Validators


@pytest.mark.parametrize("value", ["coffee", "0", "1", "2", "3", "5", "8", "13", "21", "split"])
def test_valid_poker_values_are_accepted(value):
    assert Validators.validate_poker_value(value) == (True, None)


@pytest.mark.parametrize("value", ["4", "100", "Coffee", "", None, 8])
def test_invalid_poker_values_are_rejected(value):
    is_valid, error = Validators.validate_poker_value(value)
    assert not is_valid
    assert error


@pytest.mark.parametrize("email", ["a@example.test", "first.last+tag@sub.example.org"])
def test_valid_emails_are_accepted(email):
    assert Validators.validate_email(email)[0]


@pytest.mark.parametrize("email", ["notanemail", "a@b", "@example.test"])
def test_invalid_emails_are_rejected(email):
    assert not Validators.validate_email(email)[0]


def test_room_id_format():
    assert Validators.validate_room_id("room-abcd1234")[0]
    assert not Validators.validate_room_id("room-abc")[0]
    assert not Validators.validate_room_id("../etc/passwd")[0]


def test_grid_must_be_five_by_five():
    grid = [["x"] * 5 for _ in range(5)]
    assert Validators.validate_grid(grid)[0]
    assert not Validators.validate_grid(grid[:4])[0]
    assert not Validators.validate_grid([["x"] * 4 for _ in range(5)])[0]
