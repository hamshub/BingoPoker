"""End-to-end tests of the room WebSocket protocol."""

import asyncio

from handlers import websocket
from tests.conftest import create_room, register


async def receive_type(ws, msg_type: str, timeout: float = 2.0) -> dict:
    """Read messages until one of the given type arrives."""
    async def _read():
        while True:
            msg = await ws.receive_json()
            if msg["type"] == msg_type:
                return msg["payload"]
    return await asyncio.wait_for(_read(), timeout)


async def assert_no_message(ws, msg_type: str, timeout: float = 0.3) -> None:
    try:
        await receive_type(ws, msg_type, timeout)
    except asyncio.TimeoutError:
        return
    raise AssertionError(f"unexpected {msg_type} message")


async def join(client, room_id: str, email: str):
    ws = await client.ws_connect(f"/ws/{room_id}/{email}")
    await receive_type(ws, "room_state")
    return ws


async def two_player_room(client):
    alice = await register(client, "alice")
    bob = await register(client, "bob")
    room_id = await create_room(client, alice)
    ws_a = await join(client, room_id, alice)
    ws_b = await join(client, room_id, bob)
    await receive_type(ws_a, "user_joined")
    return room_id, (alice, ws_a), (bob, ws_b)


async def test_unknown_user_is_rejected(client):
    alice = await register(client, "alice")
    room_id = await create_room(client, alice)

    resp = await client.get(f"/ws/{room_id}/nobody@example.test")

    assert resp.status == 401


async def test_room_state_includes_round_fields(client):
    alice = await register(client, "alice")
    room_id = await create_room(client, alice)

    ws = await client.ws_connect(f"/ws/{room_id}/{alice}")
    state = await receive_type(ws, "room_state")

    session = state["session"]
    assert [u["email"] for u in session["users"]] == [alice]
    assert session["ready"] == []
    assert session["auto_reveal"] is False
    assert session["revealed"] is False


async def test_bingo_selection_is_broadcast(client):
    _, (alice, ws_a), (_, ws_b) = await two_player_room(client)

    await ws_a.send_json({"type": "bingo_select", "payload": {"row": 1, "col": 2}})

    payload = await receive_type(ws_b, "bingo_updated")
    assert payload["bingo_selections"][alice] == [[1, 2]]


async def test_poker_value_is_hidden_until_reveal(client):
    _, (alice, ws_a), (_, ws_b) = await two_player_room(client)

    await ws_a.send_json({"type": "poker_select", "payload": {"value": "coffee"}})

    payload = await receive_type(ws_b, "poker_updated")
    assert payload == {"email": alice, "has_selection": True}

    await ws_b.send_json({"type": "reveal", "payload": {}})
    revealed = await receive_type(ws_b, "revealed")
    assert revealed["poker_selections"] == {alice: "coffee"}


async def test_ready_toggle_is_broadcast(client):
    _, (alice, ws_a), (_, ws_b) = await two_player_room(client)

    await ws_a.send_json({"type": "ready_toggle", "payload": {}})
    assert (await receive_type(ws_b, "ready_updated"))["ready"] == [alice]

    await ws_a.send_json({"type": "ready_toggle", "payload": {}})
    assert (await receive_type(ws_b, "ready_updated"))["ready"] == []


async def test_auto_reveal_fires_when_last_user_is_ready(client):
    _, (_, ws_a), (_, ws_b) = await two_player_room(client)
    await ws_a.send_json({"type": "auto_reveal_set", "payload": {"enabled": True}})
    assert (await receive_type(ws_b, "auto_reveal_updated"))["enabled"] is True

    await ws_a.send_json({"type": "ready_toggle", "payload": {}})
    await assert_no_message(ws_b, "revealed")

    await ws_b.send_json({"type": "ready_toggle", "payload": {}})
    await receive_type(ws_a, "revealed")


async def test_no_auto_reveal_when_setting_is_off(client):
    _, (_, ws_a), (_, ws_b) = await two_player_room(client)

    await ws_a.send_json({"type": "ready_toggle", "payload": {}})
    await ws_b.send_json({"type": "ready_toggle", "payload": {}})

    await assert_no_message(ws_a, "revealed")


async def test_auto_reveal_fires_when_unready_user_leaves(client):
    _, (_, ws_a), (_, ws_b) = await two_player_room(client)
    await ws_a.send_json({"type": "auto_reveal_set", "payload": {"enabled": True}})
    await ws_a.send_json({"type": "ready_toggle", "payload": {}})
    await receive_type(ws_a, "ready_updated")

    await ws_b.close()

    await receive_type(ws_a, "revealed")


async def test_reset_clears_ready_flags(client):
    _, (_, ws_a), (_, ws_b) = await two_player_room(client)
    await ws_a.send_json({"type": "ready_toggle", "payload": {}})
    await receive_type(ws_b, "ready_updated")

    await ws_a.send_json({"type": "reset", "payload": {}})
    await receive_type(ws_b, "round_reset")

    room_id = next(iter(client.app["room_manager"].sessions))
    assert client.app["room_manager"].sessions[room_id]["ready"] == []


async def test_unknown_message_type_returns_error(client):
    _, (_, ws_a), _ = await two_player_room(client)

    await ws_a.send_json({"type": "nonsense", "payload": {}})

    assert "Unknown type" in (await receive_type(ws_a, "error"))["message"]


async def test_broadcast_skips_and_prunes_failing_socket(client):
    room_id, (alice, ws_a), (bob, _) = await two_player_room(client)

    class BrokenSocket:
        closed = False

        async def send_json(self, message):
            raise ConnectionResetError("gone")

    websocket._connections[room_id][bob] = BrokenSocket()

    await ws_a.send_json({"type": "bingo_select", "payload": {"row": 0, "col": 0}})

    # Alice still receives the broadcast despite Bob's socket failing
    payload = await receive_type(ws_a, "bingo_updated")
    assert payload["bingo_selections"][alice] == [[0, 0]]
    assert bob not in websocket._connections[room_id]


async def test_join_and_reveal_are_recorded_in_analytics(client):
    _, (_, ws_a), (_, ws_b) = await two_player_room(client)
    await ws_a.send_json({"type": "poker_select", "payload": {"value": "5"}})
    await receive_type(ws_b, "poker_updated")

    await ws_a.send_json({"type": "reveal", "payload": {}})
    await receive_type(ws_b, "revealed")
    # A second reveal click is re-broadcast but not double counted
    await ws_b.send_json({"type": "reveal", "payload": {}})
    await receive_type(ws_a, "revealed")

    totals = client.app["analytics_manager"].get_summary()["totals"]
    assert totals["rooms_created"] == 1
    assert totals["joins"] == 2
    assert totals["rounds_revealed"] == 1
    assert totals["votes_cast"] == 1
