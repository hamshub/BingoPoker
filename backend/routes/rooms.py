"""Room REST API routes.

Endpoints:
- POST /api/room - Create new room
- GET /api/room/{room_id} - Get room state
- GET /api/rooms - List all rooms
- DELETE /api/room/{room_id} - Delete a room (creator only)

The WebSocket endpoint lives in handlers/websocket.py.
"""

import logging
from aiohttp import web
from utils.validators import Validators

logger = logging.getLogger(__name__)


async def create_room_handler(request: web.Request) -> web.Response:
    """
    POST /api/room - Create a new room.
    
    Request body: {
        "name": "Room Name",
        "grid": [["Cell1", "Cell2", ...], ...],  # 5x5 array of strings
        "created_by": "email@example.com"
    }
    Response: {"room_id": "room-XXXXXXXX", "room": {name, config, created_at, created_by}}
    """
    try:
        data = await request.json()
        name = data.get("name")
        grid = data.get("grid")
        created_by = data.get("created_by")
        
        # Validate inputs
        valid, error = Validators.validate_room_name(name)
        if not valid:
            return web.json_response(
                {"error": "invalid_room_name", "message": error},
                status=400
            )
        
        valid, error = Validators.validate_grid(grid)
        if not valid:
            return web.json_response(
                {"error": "invalid_grid", "message": error},
                status=400
            )
        
        if not created_by:
            return web.json_response(
                {"error": "invalid_input", "message": "created_by (email) required"},
                status=400
            )

        creator_id = request.app["user_manager"].resolve_user_id(created_by)
        if not creator_id:
            return web.json_response(
                {"error": "user_not_found", "message": "Creator is not a registered user"},
                status=404
            )
        
        # Create room
        room_manager = request.app["room_manager"]

        # Block duplicate room names
        active_rooms = await room_manager.get_active_rooms()
        if any(r.get("name") == name for r in active_rooms.values()):
            return web.json_response(
                {"error": "duplicate_name", "message": f"A room named '{name}' already exists"},
                status=409
            )

        success, error, room_data = await room_manager.create_room(name, grid, creator_id)

        if not success:
            return web.json_response(
                {"error": "creation_failed", "message": error},
                status=400
            )

        room_id = room_data["room_id"]
        logger.info(f"Room created: {room_id} ('{name}' by user {creator_id})")

        return web.json_response({
            "room_id": room_id,
            "message": "Room created successfully"
        }, status=201)
    
    except ValueError:
        return web.json_response(
            {"error": "invalid_json", "message": "Invalid JSON in request body"},
            status=400
        )
    except Exception as e:
        return web.json_response(
            {"error": "server_error", "message": str(e)},
            status=500
        )


async def get_room_handler(request: web.Request) -> web.Response:
    """
    GET /api/room/{room_id} - Get room state and configuration.
    
    Response: {
        "room": {
            "config": {name, grid, created_at, created_by},
            "session": {users: [...], bingo_selections: {...}, poker_selections: {...}, revealed: bool}
        }
    }
    """
    try:
        room_id = request.match_info.get("room_id")
        
        # Validate room_id format
        valid, error = Validators.validate_room_id(room_id)
        if not valid:
            return web.json_response(
                {"error": "invalid_room_id", "message": error},
                status=400
            )
        
        room_manager = request.app["room_manager"]
        
        # Get room configuration
        room_config = await room_manager.get_room(room_id)
        if not room_config:
            return web.json_response(
                {"error": "room_not_found", "message": f"Room {room_id} not found"},
                status=404
            )
        
        # Get room state (config + session)
        room_state = await room_manager.get_room_state(room_id)
        
        return web.json_response({
            "room_id": room_id,
            "room": room_state
        }, status=200)
    
    except Exception as e:
        return web.json_response(
            {"error": "server_error", "message": str(e)},
            status=500
        )


async def list_rooms_handler(request: web.Request) -> web.Response:
    """
    GET /api/rooms - List all active rooms with user counts.
    
    Response: {
        "rooms": [
            {
                "room_id": "room-XXXXXXXX",
                "name": "Room Name",
                "user_count": 3,
                "created_at": "2026-08-12T10:00:00",
                "created_by": "<user_id>"
            },
            ...
        ]
    }
    """
    try:
        room_manager = request.app["room_manager"]
        
        # Get all active rooms
        all_rooms = await room_manager.get_active_rooms()
        
        # Build response with room summaries
        rooms_list = []
        for room_id, room_config in all_rooms.items():
            session = room_manager.sessions.get(room_id, {})
            user_count = len(session.get("users", []))

            rooms_list.append({
                "room_id": room_id,
                "name": room_config.get("name"),
                "user_count": user_count,
                "created_at": room_config.get("created_at"),
                "created_by": room_config.get("created_by")
            })
        
        return web.json_response({
            "rooms": rooms_list,
            "count": len(rooms_list)
        }, status=200)
    
    except Exception as e:
        return web.json_response(
            {"error": "server_error", "message": str(e)},
            status=500
        )


async def delete_room_handler(request: web.Request) -> web.Response:
    """
    DELETE /api/room/{room_id} - Delete a room.
    
    Request body: {"created_by": "creator@example.com"}
    Response: {"message": "Room deleted successfully"}
    """
    try:
        room_id = request.match_info.get("room_id")
        data = await request.json()
        created_by = data.get("created_by")
        
        # Validate room_id format
        valid, error = Validators.validate_room_id(room_id)
        if not valid:
            return web.json_response(
                {"error": "invalid_room_id", "message": error},
                status=400
            )
        
        if not created_by:
            return web.json_response(
                {"error": "invalid_input", "message": "created_by (email) required"},
                status=400
            )
        
        requester_id = request.app["user_manager"].resolve_user_id(created_by)
        room_manager = request.app["room_manager"]
        
        # Get room configuration
        room_config = await room_manager.get_room(room_id)
        if not room_config:
            return web.json_response(
                {"error": "room_not_found", "message": f"Room {room_id} not found"},
                status=404
            )
        
        # Check if requester is the creator
        if not requester_id or room_config.get("created_by") != requester_id:
            return web.json_response(
                {"error": "unauthorized", "message": "Only the room creator can delete this room"},
                status=403
            )
        
        # Delete room
        success, error = await room_manager.delete_room(room_id)
        
        if not success:
            return web.json_response(
                {"error": "deletion_failed", "message": error},
                status=400
            )
        
        logger.info(f"Room deleted: {room_id} ('{room_config.get('name')}' by user {requester_id})")
        
        return web.json_response({
            "message": "Room deleted successfully"
        }, status=200)
    
    except ValueError:
        return web.json_response(
            {"error": "invalid_json", "message": "Invalid JSON in request body"},
            status=400
        )
    except Exception as e:
        return web.json_response(
            {"error": "server_error", "message": str(e)},
            status=500
        )


def setup_room_routes(app: web.Application) -> None:
    app.router.add_post("/api/room", create_room_handler)
    app.router.add_get("/api/room/{room_id}", get_room_handler)
    app.router.add_get("/api/rooms", list_rooms_handler)
    app.router.add_delete("/api/room/{room_id}", delete_room_handler)
