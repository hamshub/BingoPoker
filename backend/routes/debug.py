"""Temporary debug endpoints for clearing persisted data during development."""

import aiofiles
import json
from aiohttp import web


async def delete_users_handler(request: web.Request) -> web.Response:
    user_manager = request.app["user_manager"]
    user_manager.users = {}
    async with aiofiles.open(user_manager.users_file, "w") as f:
        await f.write(json.dumps({}))
    return web.json_response({"message": "All users deleted"})


async def delete_rooms_handler(request: web.Request) -> web.Response:
    room_manager = request.app["room_manager"]
    room_manager.rooms = {}
    room_manager.sessions = {}
    async with aiofiles.open(room_manager.rooms_file, "w") as f:
        await f.write(json.dumps({}))
    return web.json_response({"message": "All rooms deleted"})


def setup_debug_routes(app: web.Application) -> None:
    app.router.add_delete("/api/debug/users", delete_users_handler)
    app.router.add_delete("/api/debug/rooms", delete_rooms_handler)
