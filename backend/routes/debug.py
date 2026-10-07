"""Temporary debug endpoints for clearing persisted data during development."""

from aiohttp import web

from utils.file_io import write_json_atomic


async def delete_users_handler(request: web.Request) -> web.Response:
    user_manager = request.app["user_manager"]
    user_manager.users = {}
    user_manager._by_email_hash = {}
    await write_json_atomic(user_manager.users_file, {})
    return web.json_response({"message": "All users deleted"})


async def delete_rooms_handler(request: web.Request) -> web.Response:
    room_manager = request.app["room_manager"]
    room_manager.rooms = {}
    room_manager.sessions = {}
    await write_json_atomic(room_manager.rooms_file, {})
    return web.json_response({"message": "All rooms deleted"})


def setup_debug_routes(app: web.Application) -> None:
    app.router.add_delete("/api/debug/users", delete_users_handler)
    app.router.add_delete("/api/debug/rooms", delete_rooms_handler)
