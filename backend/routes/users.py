"""User REST API routes.

Endpoints:
- POST /api/user - Register or get user
- GET /api/user/{email} - Get user profile
- PUT /api/user/{email} - Update username and/or role
"""

import logging
from aiohttp import web

logger = logging.getLogger(__name__)


async def register_user_handler(request: web.Request) -> web.Response:
    """
    POST /api/user - Register new user or get existing user.
    
    Request body: {"email": "user@example.com", "username": "John"}
    Response: {"user": {user_id, email, username, role}, "is_new": bool}
    """
    try:
        data = await request.json()
        email = data.get("email")
        username = data.get("username")
        role = data.get("role", "worker")

        if not email or not username:
            return web.json_response(
                {"error": "invalid_input", "message": "Email and username required"},
                status=400
            )

        # Get user manager from app
        user_manager = request.app["user_manager"]

        # Check if user already exists
        is_new = not await user_manager.user_exists(email)

        # Register or get user
        if is_new:
            success, error, user = await user_manager.register_user(email, username, role)
            if not success:
                return web.json_response(
                    {"error": "registration_failed", "message": error},
                    status=400
                )
            logger.info(f"New user registered: {user['user_id']} ({username}, role: {role})")
            return web.json_response({
                "user": user,
                "is_new": True
            }, status=201)
        else:
            # User exists, fetch their profile
            user = await user_manager.get_user(email)
            logger.info(f"User login: {user['user_id']} ({user.get('username')})")
            return web.json_response({
                "user": user,
                "is_new": False
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


async def get_user_handler(request: web.Request) -> web.Response:
    """
    GET /api/user/{email} - Get user profile.
    
    Response: {"user": {user_id, email, username, role}}
    """
    try:
        email = request.match_info.get("email")
        
        if not email:
            return web.json_response(
                {"error": "invalid_input", "message": "Email required"},
                status=400
            )
        
        user_manager = request.app["user_manager"]
        user = await user_manager.get_user(email)
        
        if not user:
            return web.json_response(
                {"error": "user_not_found", "message": f"User {email} not found"},
                status=404
            )
        
        return web.json_response({"user": user}, status=200)
    
    except Exception as e:
        return web.json_response(
            {"error": "server_error", "message": str(e)},
            status=500
        )


async def update_user_handler(request: web.Request) -> web.Response:
    """
    PUT /api/user/{email} - Update user username or role.
    
    Request body: {"username": "NewName"} or {"role": "worker" or "observer"}
    Response: {"user": {user_id, email, username, role}}
    """
    try:
        email = request.match_info.get("email")
        data = await request.json()
        new_username = data.get("username")
        new_role = data.get("role")
        
        if not email:
            return web.json_response(
                {"error": "invalid_input", "message": "Email required"},
                status=400
            )
        
        if not new_username and not new_role:
            return web.json_response(
                {"error": "invalid_input", "message": "Username or role required"},
                status=400
            )
        
        user_manager = request.app["user_manager"]
        
        # Check if user exists first
        if not await user_manager.user_exists(email):
            return web.json_response(
                {"error": "user_not_found", "message": f"User {email} not found"},
                status=404
            )
        
        # Update username if provided
        if new_username:
            success, error = await user_manager.update_username(email, new_username)
            if not success:
                return web.json_response(
                    {"error": "update_failed", "message": error},
                    status=400
                )
        
        # Update role if provided
        if new_role:
            success, error = await user_manager.update_role(email, new_role)
            if not success:
                return web.json_response(
                    {"error": "update_failed", "message": error},
                    status=400
                )
        
        # Return updated user
        user = await user_manager.get_user(email)
        
        return web.json_response({"user": user}, status=200)
    
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


def setup_user_routes(app: web.Application) -> None:
    """
    Register user routes with the app.
    
    Args:
        app: aiohttp Application instance
    """
    app.router.add_post("/api/user", register_user_handler)
    app.router.add_get("/api/user/{email}", get_user_handler)
    app.router.add_put("/api/user/{email}", update_user_handler)
