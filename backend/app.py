"""BingoPoker - Main aiohttp application setup.

Initializes the web server, managers, and routes.
Run with: python backend/app.py
"""

import os
from aiohttp import web
from dotenv import load_dotenv

from utils.user_manager import UserManager
from utils.room_manager import RoomManager
from routes.users import setup_user_routes
from routes.rooms import setup_room_routes
from routes.debug import setup_debug_routes
from handlers.websocket import room_websocket_handler


# Load environment variables
load_dotenv()

# Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8081"))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
DATA_DIR = os.getenv(
    "DATA_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
)
# Relative paths are resolved against app.py's directory, not CWD
if not os.path.isabs(DATA_DIR):
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_DIR)


async def startup_handler(app: web.Application) -> None:
    """
    Handle startup events.

    Load manager data from disk.
    """
    user_manager = UserManager(data_dir=DATA_DIR)
    room_manager = RoomManager(data_dir=DATA_DIR)

    await user_manager.load()
    await room_manager.load()

    # Store managers in app context for access in request handlers
    app["user_manager"] = user_manager
    app["room_manager"] = room_manager

    print(f"Loaded {len(user_manager.users)} users")
    print(f"Loaded {len(room_manager.rooms)} room configurations")


async def cleanup_handler(app: web.Application) -> None:
    """
    Handle shutdown events.

    Clean up resources.
    """
    print("Server shutting down")


async def health_check_handler(request: web.Request) -> web.Response:
    """
    Health check endpoint.

    Returns:
        200 OK with status
    """
    return web.json_response({"status": "ok", "service": "BingoPoker API"})


async def serve_index_handler(request: web.Request) -> web.FileResponse:
    """
    Serve index.html for root path.

    Returns:
        index.html content
    """
    index_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    return web.FileResponse(index_path)


def create_app() -> web.Application:
    """
    Create and configure the aiohttp application.

    Returns:
        Configured Application instance
    """
    app = web.Application()

    # Startup/cleanup handlers
    app.on_startup.append(startup_handler)
    app.on_cleanup.append(cleanup_handler)

    # Routes
    app.router.add_get("/health", health_check_handler)
    app.router.add_get("/", serve_index_handler)

    # Setup route modules
    setup_user_routes(app)
    setup_room_routes(app)
    setup_debug_routes(app)
    app.router.add_get("/ws/{room_id}/{user_email}", room_websocket_handler)

    # Static files served directly under /css and /js
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
    app.router.add_static("/css", os.path.join(frontend_path, "css"))
    app.router.add_static("/js", os.path.join(frontend_path, "js"))
    app.router.add_static("/templates", os.path.join(frontend_path, "templates"))

    return app


if __name__ == "__main__":
    app = create_app()
    print(f"Starting BingoPoker on {HOST}:{PORT}")
    web.run_app(app, host=HOST, port=PORT, print=lambda *args: None)
