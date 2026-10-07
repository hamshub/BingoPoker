"""Tests for RoomManager persistence and round state."""

import json

import pytest

from utils.room_manager import RoomManager

GRID = [["x"] * 5 for _ in range(5)]


@pytest.fixture
async def manager(tmp_path):
    rm = RoomManager(data_dir=str(tmp_path))
    await rm.load()
    return rm


async def make_room(rm, *emails):
    _, _, room = await rm.create_room("Room", GRID, "creator-id")
    room_id = room["room_id"]
    for email in emails:
        await rm.add_user_to_session(room_id, email, {"email": email, "username": email, "role": "worker"})
    return room_id


async def test_rooms_persist_across_reload(tmp_path, manager):
    room_id = await make_room(manager)

    reloaded = RoomManager(data_dir=str(tmp_path))
    await reloaded.load()

    assert reloaded.rooms[room_id]["name"] == "Room"
    assert not list(tmp_path.glob("*.tmp")), "atomic write left a temp file behind"


async def test_explicit_coffee_vote_is_stored(manager):
    room_id = await make_room(manager, "a@example.test")

    success, _ = await manager.record_poker_selection(room_id, "a@example.test", "coffee")

    assert success
    assert manager.sessions[room_id]["poker_selections"] == {"a@example.test": "coffee"}


async def test_invalid_poker_value_is_rejected(manager):
    room_id = await make_room(manager, "a@example.test")

    success, _ = await manager.record_poker_selection(room_id, "a@example.test", "7")

    assert not success
    assert manager.sessions[room_id]["poker_selections"] == {}


async def test_toggle_ready_flips_membership(manager):
    room_id = await make_room(manager, "a@example.test")

    await manager.toggle_ready(room_id, "a@example.test")
    assert manager.sessions[room_id]["ready"] == ["a@example.test"]

    await manager.toggle_ready(room_id, "a@example.test")
    assert manager.sessions[room_id]["ready"] == []


async def test_reset_clears_round_but_keeps_auto_reveal(manager):
    room_id = await make_room(manager, "a@example.test")
    await manager.set_auto_reveal(room_id, True)
    await manager.toggle_ready(room_id, "a@example.test")
    await manager.record_poker_selection(room_id, "a@example.test", "8")
    await manager.record_bingo_selection(room_id, "a@example.test", 1, 1)
    await manager.reveal_round(room_id)

    await manager.reset_round(room_id)

    session = manager.sessions[room_id]
    assert session["ready"] == []
    assert session["poker_selections"] == {}
    assert session["bingo_selections"] == {}
    assert session["revealed"] is False
    assert session["auto_reveal"] is True


async def test_leaving_removes_user_state(manager):
    room_id = await make_room(manager, "a@example.test", "b@example.test")
    await manager.toggle_ready(room_id, "a@example.test")
    await manager.record_poker_selection(room_id, "a@example.test", "5")

    await manager.remove_user_from_session(room_id, "a@example.test")

    session = manager.sessions[room_id]
    assert "a@example.test" not in session["ready"]
    assert "a@example.test" not in session["poker_selections"]


async def test_set_auto_reveal_rejects_non_boolean(manager):
    room_id = await make_room(manager, "a@example.test")

    success, _ = await manager.set_auto_reveal(room_id, "yes")

    assert not success
    assert manager.sessions[room_id]["auto_reveal"] is False


async def test_should_auto_reveal_requires_setting_and_everyone_ready(manager):
    room_id = await make_room(manager, "a@example.test", "b@example.test")
    await manager.toggle_ready(room_id, "a@example.test")
    await manager.toggle_ready(room_id, "b@example.test")
    assert not manager.should_auto_reveal(room_id), "setting is off"

    await manager.set_auto_reveal(room_id, True)
    assert manager.should_auto_reveal(room_id)

    await manager.toggle_ready(room_id, "b@example.test")
    assert not manager.should_auto_reveal(room_id), "b is no longer ready"

    await manager.toggle_ready(room_id, "b@example.test")
    await manager.reveal_round(room_id)
    assert not manager.should_auto_reveal(room_id), "already revealed"


async def test_corrupt_rooms_file_does_not_crash_load(tmp_path):
    (tmp_path / "rooms.json").write_text("{not json", encoding="utf-8")

    rm = RoomManager(data_dir=str(tmp_path))
    await rm.load()

    assert rm.rooms == {}


async def test_saved_file_is_valid_json(tmp_path, manager):
    await make_room(manager)

    data = json.loads((tmp_path / "rooms.json").read_text(encoding="utf-8"))

    assert len(data) == 1
