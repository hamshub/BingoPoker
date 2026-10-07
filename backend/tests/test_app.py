"""Tests for app-level endpoints, persistence privacy, logging, and admin pages."""

import base64
import json
import logging
from logging.handlers import TimedRotatingFileHandler

from aiohttp.test_utils import TestClient

from app import create_app
from tests.conftest import ADMIN_PASSWORD, register


def basic_auth(password: str, user: str = "admin") -> dict:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


async def test_health_and_version(client):
    health = await client.get("/health")
    version = await client.get("/api/version")

    assert health.status == 200
    body = await version.json()
    assert set(body) == {"version", "build_date"}


async def test_emails_are_never_written_to_disk(client, data_dir):
    await register(client, "alice")

    users_json = (data_dir / "users.json").read_text(encoding="utf-8")

    assert "alice@example.test" not in users_json
    assert json.loads(users_json)


async def test_log_file_rotates_daily_and_keeps_30(client, log_dir):
    handlers = [h for h in logging.getLogger().handlers if isinstance(h, TimedRotatingFileHandler)]

    assert len(handlers) == 1
    assert handlers[0].when == "MIDNIGHT"
    assert handlers[0].backupCount == 30
    assert (log_dir / "bingopoker.log").exists()


async def test_admin_pages_require_password(client):
    for path in ("/logs", "/analytics"):
        resp = await client.get(path)
        assert resp.status == 401
        assert "Basic" in resp.headers["WWW-Authenticate"]


async def test_wrong_password_is_rejected(client):
    resp = await client.get("/logs", headers=basic_auth("wrong"))

    assert resp.status == 401


async def test_logs_page_shows_current_log(client):
    logging.getLogger("test").info("marker line for the logs page")

    resp = await client.get("/logs", headers=basic_auth(ADMIN_PASSWORD))

    assert resp.status == 200
    assert resp.headers["Cache-Control"] == "no-store"
    assert "marker line for the logs page" in await resp.text()


async def test_logs_page_lists_rotated_files(client, log_dir):
    (log_dir / "bingopoker.log.2026-10-01").write_text("old day\n", encoding="utf-8")

    listing = await (await client.get("/logs", headers=basic_auth(ADMIN_PASSWORD))).text()
    old = await client.get("/logs?file=bingopoker.log.2026-10-01", headers=basic_auth(ADMIN_PASSWORD))

    assert "2026-10-01" in listing
    assert "old day" in await old.text()


async def test_logs_page_rejects_unlisted_files(client):
    for name in ("../data/users.json", "users.json", "bingopoker.log/../../x"):
        resp = await client.get("/logs", params={"file": name}, headers=basic_auth(ADMIN_PASSWORD))
        assert resp.status == 404


async def test_analytics_page_renders(client):
    await register(client, "alice")

    resp = await client.get("/analytics", headers=basic_auth(ADMIN_PASSWORD))

    assert resp.status == 200
    text = await resp.text()
    assert "Registered users" in text
    assert "Vote distribution" in text


async def test_admin_pages_disabled_without_password(aiohttp_client, data_dir, log_dir):
    app = create_app(data_dir=data_dir, log_dir=log_dir, admin_password="")
    client: TestClient = await aiohttp_client(app)

    resp = await client.get("/logs", headers=basic_auth(""))

    assert resp.status == 404
