"""BingoPoker - Main aiohttp application setup.

Initializes the web server, managers, and routes.
Run with: python backend/app.py
"""

import os
import logging
from logging.handlers import TimedRotatingFileHandler
from typing import Optional
from aiohttp import web
from dotenv import load_dotenv
from pathlib import Path

from utils.user_manager import UserManager
from utils.room_manager import RoomManager
from utils.analytics_manager import AnalyticsManager
from routes.users import setup_user_routes
from routes.rooms import setup_room_routes
from routes.debug import setup_debug_routes
from routes.admin import setup_admin_routes
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

# Defaults to backend/logs; Docker points it inside the data volume so logs survive updates
LOG_DIR = Path(os.getenv("LOG_DIR", DATA_DIR.parent / "logs"))

# Admin pages (/logs, /analytics) are only mounted when a password is configured
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# Injected at image build time by the GitHub Action
APP_VERSION = os.getenv("APP_VERSION", "dev")
BUILD_DATE = os.getenv("BUILD_DATE", "")

# Rotated daily; days without any log lines produce no file
LOG_RETENTION_FILES = 30


def _setup_logging(log_dir: Path) -> None:
    """
    Configure logging to a daily-rotated file and the console.

    Args:
        log_dir: Directory where log files are stored
    """
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "bingopoker.log")

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Replace handlers from an earlier app instance (tests create several)
    for handler in [h for h in logger.handlers if getattr(h, "_bingopoker", False)]:
        logger.removeHandler(handler)
        handler.close()

    # File handler - logs all events, one file per day, 30 files kept
    file_handler = TimedRotatingFileHandler(
        log_file, when="midnight", backupCount=LOG_RETENTION_FILES, encoding="utf-8"
    )
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
    file_handler._bingopoker = True
    console_handler._bingopoker = True
    
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
    data_dir = app["data_dir"]
    os.makedirs(data_dir, exist_ok=True)

    # Configure logging
    _setup_logging(app["log_dir"])

    logger = logging.getLogger(__name__)
    logger.info(f"Starting BingoPoker application (version {APP_VERSION})")

    user_manager = UserManager(data_dir=str(data_dir))
    room_manager = RoomManager(data_dir=str(data_dir))
    analytics_manager = AnalyticsManager(data_dir=str(data_dir))

    await user_manager.load()
    await room_manager.load()
    await room_manager.migrate_creator_ids(user_manager.resolve_user_id)
    await analytics_manager.load()

    # Store managers in app context for access in request handlers
    app["user_manager"] = user_manager
    app["room_manager"] = room_manager
    app["analytics_manager"] = analytics_manager

    if not app["admin_password"]:
        logger.warning("ADMIN_PASSWORD is not set; /logs and /analytics are disabled")
    
    logger.info(f"Loaded {len(user_manager.users)} users and {len(room_manager.rooms)} rooms")


async def cleanup_handler(app: web.Application) -> None:
    """
    Handle shutdown events.

    Clean up resources.
    """
    logger = logging.getLogger(__name__)
    logger.info("Server shutting down")

    # Release the log file so it can be rotated or deleted (tests use temp dirs)
    root = logging.getLogger()
    for handler in [h for h in root.handlers if getattr(h, "_bingopoker", False)]:
        root.removeHandler(handler)
        handler.close()


async def health_check_handler(request: web.Request) -> web.Response:
    """
    Health check endpoint.

    Returns:
        200 OK with status
    """
    return web.json_response({"status": "ok", "service": "BingoPoker API", "version": APP_VERSION})


async def version_handler(request: web.Request) -> web.Response:
    """
    Report the running build.

    Returns:
        200 OK with { version, build_date }
    """
    return web.json_response({"version": APP_VERSION, "build_date": BUILD_DATE})


async def serve_index_handler(request: web.Request) -> web.FileResponse:
    """
    Serve index.html for root path.

    Returns:
        index.html content
    """
    index_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    return web.FileResponse(index_path)


def create_app(
    data_dir: Optional[Path] = None,
    log_dir: Optional[Path] = None,
    admin_password: Optional[str] = None,
) -> web.Application:
    """
    Create and configure the aiohttp application.

    Args:
        data_dir: Where JSON data is stored (defaults to DATA_DIR)
        log_dir: Where log files are written (defaults to LOG_DIR)
        admin_password: Password for /logs and /analytics (defaults to ADMIN_PASSWORD)

    Returns:
        Configured Application instance
    """
    app = web.Application()
    app["data_dir"] = Path(data_dir or DATA_DIR)
    app["log_dir"] = Path(log_dir or LOG_DIR)
    app["admin_password"] = ADMIN_PASSWORD if admin_password is None else admin_password

    # Startup/cleanup handlers
    app.on_startup.append(startup_handler)
    app.on_cleanup.append(cleanup_handler)

    # Routes
    app.router.add_get("/health", health_check_handler)
    app.router.add_get("/api/version", version_handler)
    app.router.add_get("/", serve_index_handler)

    # Setup route modules
    setup_user_routes(app)
    setup_room_routes(app)
    # Debug routes wipe all persisted data, so they stay out of production builds
    if DEBUG:
        setup_debug_routes(app)
    if app["admin_password"]:
        setup_admin_routes(app)
    app.router.add_get("/ws/{room_id}/{user_email}", room_websocket_handler)

    # Static files served directly under /css and /js
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
    app.router.add_static("/css", os.path.join(frontend_path, "css"))
    app.router.add_static("/imgs", os.path.join(frontend_path, "imgs"))
    app.router.add_static("/js", os.path.join(frontend_path, "js"))
    app.router.add_static("/templates", os.path.join(frontend_path, "templates"))

    return app


if __name__ == "__main__":
    app = create_app()
    print(f"Starting BingoPoker on {HOST}:{PORT}")
    web.run_app(app, host=HOST, port=PORT, print=lambda *args: None)
