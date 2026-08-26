"""BingoPoker - Main aiohttp application setup.

Initializes the web server, managers, and routes.
Run with: python backend/app.py
"""

import os
import logging
from aiohttp import web
from dotenv import load_dotenv
from pathlib import Path

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
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

DATA_DIR = Path(
    os.getenv(
        "DATA_DIR",
        Path(__file__).resolve().parent / "data"
    )
)

DATA_DIR.mkdir(parents=True, exist_ok=True)

def _setup_logging(data_dir: str) -> None:
    """
    Configure logging to file and console.
    
    Args:
        data_dir: Directory where logs should be stored
    """
    log_dir = os.path.join(os.path.dirname(data_dir), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "bingopoker.log")
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # File handler - logs all events
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Console handler - logs warnings and errors only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Suppress asyncio connection reset errors in event loop
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Drop per-request access logs; they are noisy and echo user emails in URLs
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)


async def startup_handler(app: web.Application) -> None:
    """
    Handle startup events.

    Load manager data from disk and configure logging.
    """
    # Configure logging
    _setup_logging(DATA_DIR)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting BingoPoker application")
    
    user_manager = UserManager(data_dir=DATA_DIR)
    room_manager = RoomManager(data_dir=DATA_DIR)

    await user_manager.load()
    await room_manager.load()
    await room_manager.migrate_creator_ids(user_manager.resolve_user_id)

    # Store managers in app context for access in request handlers
    app["user_manager"] = user_manager
    app["room_manager"] = room_manager
    
    logger.info(f"Loaded {len(user_manager.users)} users and {len(room_manager.rooms)} rooms")


async def cleanup_handler(app: web.Application) -> None:
    """
    Handle shutdown events.

    Clean up resources.
    """
    logger = logging.getLogger(__name__)
    logger.info("Server shutting down")


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
    # Debug routes wipe all persisted data, so they stay out of production builds
    if DEBUG:
        setup_debug_routes(app)
    app.router.add_get("/ws/{room_id}/{user_email}", room_websocket_handler)

    # Static files served directly under /css and /js
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
    app.router.add_static("/css", os.path.join(frontend_path, "css"))
    app.router.add_static("/imgs", os.path.join(frontend_path, "imgs")
)
    app.router.add_static("/js", os.path.join(frontend_path, "js"))
    app.router.add_static("/templates", os.path.join(frontend_path, "templates"))

    return app


if __name__ == "__main__":
    app = create_app()
    print(f"Starting BingoPoker on {HOST}:{PORT}")
    web.run_app(app, host=HOST, port=PORT, print=lambda *args: None)
