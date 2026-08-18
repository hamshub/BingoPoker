"""WebSocket handler for BingoPoker real-time room sessions.

Manages the full lifecycle of a WebSocket connection:
join, bingo_select, poker_select, reveal, reset, disconnect.
"""

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
    await _broadcast(room_id, {
        "type": "user_joined",
        "payload": {"users": users},
    }, exclude=email)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                await _handle_message(ws, room_id, email, msg.data, room_manager)
            elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                break
    except Exception as e:
        logger.warning(f"WebSocket error for user {user_id} in room {room_id}: {type(e).__name__}: {e}")
    finally:
        await _disconnect(room_id, email, room_manager, room_name, user_id)

    return ws


async def _handle_message(
    ws: web.WebSocketResponse,
    room_id: str,
    email: str,
    raw: str,
    room_manager,
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

    elif msg_type == "reveal":
        success, _ = await room_manager.reveal_round(room_id)
        if success:
            session = room_manager.sessions[room_id]
            bingo = {e: [list(c) for c in cells] for e, cells in session["bingo_selections"].items()}
            await _broadcast(room_id, {
                "type": "revealed",
                "payload": {
                    "bingo_selections": bingo,
                    "poker_selections": session["poker_selections"],
                },
            })

    elif msg_type == "reset":
        success, _ = await room_manager.reset_round(room_id)
        if success:
            await _broadcast(room_id, {"type": "round_reset", "payload": {}})

    else:
        await ws.send_json({"type": "error", "payload": {"message": f"Unknown type: {msg_type}"}})


async def _broadcast(room_id: str, message: dict, exclude: str = None) -> None:
    room_conns = _connections.get(room_id, {})
    dead = []
    for email, ws in room_conns.items():
        if email == exclude:
            continue
        if ws.closed:
            dead.append(email)
            continue
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.debug(f"Failed to send message in {room_id}: {type(e).__name__}")
            dead.append(email)
    for email in dead:
        room_conns.pop(email, None)


async def _disconnect(
    room_id: str, email: str, room_manager, room_name: str = None, user_id: str = None
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


def _serialize_session(session: dict) -> dict:
    """Convert tuple cell coordinates to lists for JSON serialization."""
    bingo = {
        email: [list(c) for c in cells]
        for email, cells in session.get("bingo_selections", {}).items()
    }
    return {**session, "bingo_selections": bingo}
