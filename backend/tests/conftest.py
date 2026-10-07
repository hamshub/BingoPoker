"""Shared pytest fixtures for the BingoPoker backend."""

import pytest

from app import create_app

ADMIN_PASSWORD = "test-admin-password"
GRID = [[f"Cell {r}-{c}" for c in range(5)] for r in range(5)]


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def log_dir(tmp_path):
    return tmp_path / "logs"


@pytest.fixture
async def client(aiohttp_client, data_dir, log_dir):
    """A test client for a fresh app with temporary data and log directories."""
    app = create_app(data_dir=data_dir, log_dir=log_dir, admin_password=ADMIN_PASSWORD)
    return await aiohttp_client(app)


async def register(client, name: str, role: str = "worker") -> str:
    """Register a synthetic user and return their email."""
    email = f"{name}@example.test"
    resp = await client.post("/api/user", json={"email": email, "username": name, "role": role})
    assert resp.status in (200, 201)
    return email


async def create_room(client, creator_email: str, name: str = "Test Room") -> str:
    """Create a room with a placeholder grid and return its ID."""
    resp = await client.post(
        "/api/room", json={"name": name, "grid": GRID, "created_by": creator_email}
    )
    assert resp.status == 201
    return (await resp.json())["room_id"]
