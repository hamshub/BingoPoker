"""WebSocket handler for BingoPoker real-time room sessions.

Manages the full lifecycle of a WebSocket connection:
join, bingo_select, poker_select, ready_toggle, auto_reveal_set, reveal, reset, disconnect.
"""

import asyncio
import json
import logging
from aiohttp import web, WSMsgType

logger = logging.getLogger(__name__)


# Registry of active connections: {room_id: {email: ws}}
_connections: dict[str, dict[str, web.WebSocketResponse]] = {}


async def room_websocket_handler(request: web.Request) -> web.WebSocketResponse:
    room_id = request.match_info["room_id"]
    email = request.match_info["user_email"]

    user_manager = request.app["user_manager"]
    room_manager = request.app["room_manager"]
    analytics = request.app["analytics_manager"]

    # Validate user and room exist
    user = await user_manager.get_user(email)
    if not user:
        return web.Response(status=401, text="User not found")

    room = await room_manager.get_room(room_id)
    if not room:
        return web.Response(status=404, text="Room not found")

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # If same user is already connected to this room, close the old connection
    existing = _connections.get(room_id, {}).get(email)
    if existing and not existing.closed:
        await existing.send_json({"type": "replaced", "payload": {}})
        await existing.close()

    # Register connection
    _connections.setdefault(room_id, {})[email] = ws

    # Add user to session with color assigned by join order
    await room_manager.add_user_to_session(room_id, email, user)
    room_name = (await room_manager.get_room(room_id)).get('name', 'Unknown')
    user_id = user.get("user_id")
    logger.info(f"User joined room: {user_id} ({user.get('username')}) -> {room_id} ('{room_name}')")

    # Send current room state to the newly joined user
    room_state = await room_manager.get_room_state(room_id)
    room_state["session"] = _serialize_session(room_state["session"])
    await ws.send_json({"type": "room_state", "payload": room_state})

    # Broadcast updated users list to everyone else
    users = room_manager.sessions[room_id]["users"]
    await analytics.record_join(user_id, len(users))
    await _broadcast(room_id, {
        "type": "user_joined",
        "payload": {"users": users},
    }, exclude=email)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                await _handle_message(ws, room_id, email, msg.data, room_manager, analytics)
            elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                break
    except Exception as e:
        logger.warning(f"WebSocket error for user {user_id} in room {room_id}: {type(e).__name__}: {e}")
    finally:
        # aiohttp cancels the handler when the peer drops; shield so cleanup and
        # the follow-up broadcasts (user_left, auto-reveal) always run to completion
        await asyncio.shield(
            _disconnect(room_id, email, room_manager, analytics, room_name, user_id)
        )

    return ws


async def _handle_message(
    ws: web.WebSocketResponse,
    room_id: str,
    email: str,
    raw: str,
    room_manager,
    analytics,
) -> None:
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        await ws.send_json({"type": "error", "payload": {"message": "Invalid JSON"}})
        return

    msg_type = msg.get("type")
    payload = msg.get("payload", {})

    if msg_type == "bingo_select":
        row = payload.get("row")
        col = payload.get("col")
        if row is None or col is None:
            return
        success, _ = await room_manager.record_bingo_selection(room_id, email, row, col)
        if success:
            # Send full bingo_selections so clients update without a REST roundtrip
            bingo_selections = room_manager.sessions[room_id]["bingo_selections"]
            # Convert tuple keys to lists for JSON serialization
            serialized = {e: [list(c) for c in cells] for e, cells in bingo_selections.items()}
            await _broadcast(room_id, {
                "type": "bingo_updated",
                "payload": {"bingo_selections": serialized},
            })

    elif msg_type == "poker_select":
        value = payload.get("value")
        if not value:
            return
        success, _ = await room_manager.record_poker_selection(room_id, email, value)
        if success:
            await _broadcast(room_id, {
                "type": "poker_updated",
                "payload": {"email": email, "has_selection": True},
            })

    elif msg_type == "ready_toggle":
        success, _ = await room_manager.toggle_ready(room_id, email)
        if success:
            await _broadcast(room_id, {
                "type": "ready_updated",
                "payload": {"ready": room_manager.sessions[room_id]["ready"]},
            })
            await _maybe_auto_reveal(room_id, room_manager, analytics)

    elif msg_type == "auto_reveal_set":
        success, _ = await room_manager.set_auto_reveal(room_id, payload.get("enabled"))
        if success:
            await _broadcast(room_id, {
                "type": "auto_reveal_updated",
                "payload": {"enabled": room_manager.sessions[room_id]["auto_reveal"]},
            })
            await _maybe_auto_reveal(room_id, room_manager, analytics)

    elif msg_type == "reveal":
        await _reveal(room_id, room_manager, analytics)

    elif msg_type == "reset":
        success, _ = await room_manager.reset_round(room_id)
        if success:
            await _broadcast(room_id, {"type": "round_reset", "payload": {}})

    else:
        await ws.send_json({"type": "error", "payload": {"message": f"Unknown type: {msg_type}"}})


async def _reveal(room_id: str, room_manager, analytics, auto: bool = False) -> None:
    """Reveal the round and broadcast every participant's selections."""
    already_revealed = room_manager.sessions.get(room_id, {}).get("revealed", False)
    success, _ = await room_manager.reveal_round(room_id)
    if success:
        session = room_manager.sessions[room_id]
        # Repeated reveal clicks re-broadcast but are only counted once
        if not already_revealed:
            await analytics.record_reveal(
                session["poker_selections"].values(), len(session["users"]), auto
            )
        bingo = {e: [list(c) for c in cells] for e, cells in session["bingo_selections"].items()}
        await _broadcast(room_id, {
            "type": "revealed",
            "payload": {
                "bingo_selections": bingo,
                "poker_selections": session["poker_selections"],
            },
        })


async def _maybe_auto_reveal(room_id: str, room_manager, analytics) -> None:
    """Reveal the round if auto-reveal is on and every participant is ready."""
    if room_manager.should_auto_reveal(room_id):
        await _reveal(room_id, room_manager, analytics, auto=True)


# A client that cannot accept a message within this time is treated as dead
_SEND_TIMEOUT_SECONDS = 5


async def _broadcast(room_id: str, message: dict, exclude: str = None) -> None:
    """Send a message to every open socket in a room concurrently, pruning dead ones."""
    # Snapshot: connections may join or leave while the sends are awaited
    targets = [
        (email, ws) for email, ws in _connections.get(room_id, {}).items()
        if email != exclude
    ]
    if not targets:
        return

    results = await asyncio.gather(
        *(_send(ws, message) for _, ws in targets),
        return_exceptions=True,
    )

    room_conns = _connections.get(room_id, {})
    for (email, ws), result in zip(targets, results):
        if isinstance(result, BaseException) or ws.closed:
            if isinstance(result, BaseException):
                logger.debug(f"Failed to send message in {room_id}: {type(result).__name__}")
            # Only prune if a reconnect hasn't already replaced this socket
            if room_conns.get(email) is ws:
                room_conns.pop(email, None)


async def _send(ws: web.WebSocketResponse, message: dict) -> None:
    if ws.closed:
        raise ConnectionResetError("socket closed")
    await asyncio.wait_for(ws.send_json(message), _SEND_TIMEOUT_SECONDS)


async def _disconnect(
    room_id: str,
    email: str,
    room_manager,
    analytics,
    room_name: str = None,
    user_id: str = None,
) -> None:
    _connections.get(room_id, {}).pop(email, None)
    if not _connections.get(room_id):
        _connections.pop(room_id, None)

    try:
        await room_manager.remove_user_from_session(room_id, email)
        if room_name:
            logger.info(f"User left room: {user_id} <- {room_id} ('{room_name}')")
        else:
            logger.info(f"User disconnected: {user_id} <- {room_id}")
    except Exception as e:
        logger.debug(f"Error removing user from session: {type(e).__name__}: {e}")

    remaining = room_manager.sessions.get(room_id, {}).get("users", [])
    await _broadcast(room_id, {
        "type": "user_left",
        "payload": {"email": email, "users": remaining},
    })
    # The last unready participant leaving can complete the ready set
    await _maybe_auto_reveal(room_id, room_manager, analytics)


def _serialize_session(session: dict) -> dict:
    """Convert tuple cell coordinates to lists for JSON serialization."""
    bingo = {
        email: [list(c) for c in cells]
        for email, cells in session.get("bingo_selections", {}).items()
    }
    return {**session, "bingo_selections": bingo}
