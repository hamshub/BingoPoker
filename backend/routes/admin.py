"""Password-protected admin pages: /logs and /analytics.

Mounted only when ADMIN_PASSWORD is set. Uses HTTP Basic auth (any username,
the configured password), so it must be served over HTTPS (e.g. behind Caddy).
"""

import asyncio
import base64
import binascii
import hmac
import html
import logging
import os
from typing import Dict, List

from aiohttp import web

logger = logging.getLogger(__name__)

LOG_BASENAME = "bingopoker.log"
# Large log files are truncated to their tail so the page stays responsive
MAX_LOG_BYTES = 2 * 1024 * 1024
# Display order for the vote distribution
VOTE_ORDER = ["coffee", "0", "1", "2", "3", "5", "8", "13", "21", "split"]


def _is_authorized(request: web.Request) -> bool:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:], validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False
    _, _, password = decoded.partition(":")
    return hmac.compare_digest(
        password.encode("utf-8"), request.app["admin_password"].encode("utf-8")
    )


def require_admin(handler):
    """Wrap a handler with HTTP Basic auth against the admin password."""
    async def wrapped(request: web.Request) -> web.StreamResponse:
        if not _is_authorized(request):
            if "Authorization" in request.headers:
                logger.warning(f"Failed admin login for {request.path}")
                # Slow down password guessing
                await asyncio.sleep(1)
            return web.Response(
                status=401,
                text="Authentication required",
                headers={"WWW-Authenticate": 'Basic realm="BingoPoker admin", charset="UTF-8"'},
            )
        response = await handler(request)
        response.headers["Cache-Control"] = "no-store"
        return response
    return wrapped


def list_log_files(log_dir: str) -> List[str]:
    """
    List the current and rotated log files, newest first.

    Args:
        log_dir: Directory containing the logs

    Returns:
        File names such as ['bingopoker.log', 'bingopoker.log.2026-10-06', ...]
    """
    if not os.path.isdir(log_dir):
        return []
    rotated = sorted(
        (n for n in os.listdir(log_dir) if n.startswith(LOG_BASENAME + ".")),
        reverse=True,
    )
    current = [LOG_BASENAME] if os.path.exists(os.path.join(log_dir, LOG_BASENAME)) else []
    return current + rotated


async def logs_handler(request: web.Request) -> web.Response:
    """GET /logs — list log files and show the selected one (default: today's)."""
    log_dir = str(request.app["log_dir"])
    files = list_log_files(log_dir)
    selected = request.query.get("file", files[0] if files else "")

    # Only names from the listing are readable, which rules out path traversal
    if selected and selected not in files:
        return web.Response(status=404, text="Log file not found")

    content = ""
    truncated = False
    if selected:
        path = os.path.join(log_dir, selected)
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            if size > MAX_LOG_BYTES:
                f.seek(size - MAX_LOG_BYTES)
                truncated = True
            content = f.read().decode("utf-8", errors="replace")

    links = "".join(
        f'<a class="{"active" if name == selected else ""}" href="/logs?file={html.escape(name)}">'
        f'{html.escape(_log_label(name))}</a>'
        for name in files
    ) or "<p>No log files yet.</p>"
    note = '<p class="muted">Showing the last 2 MB of this file.</p>' if truncated else ""
    body = f"""
        <nav class="files">{links}</nav>
        {note}
        <pre>{html.escape(content) or "(empty)"}</pre>
    """
    return _page("Logs", body)


def _log_label(name: str) -> str:
    return "Today" if name == LOG_BASENAME else name[len(LOG_BASENAME) + 1:]


async def analytics_handler(request: web.Request) -> web.Response:
    """GET /analytics — usage statistics rendered from AnalyticsManager."""
    summary = request.app["analytics_manager"].get_summary()
    totals = summary["totals"]
    user_count = len(request.app["user_manager"].users)
    room_count = len(request.app["room_manager"].rooms)

    rounds = totals["rounds_revealed"]
    avg_participants = f'{totals["participants_in_rounds"] / rounds:.1f}' if rounds else "—"
    distribution = summary["vote_distribution"]
    votes_cast = totals["votes_cast"]
    favourite = max(distribution, key=distribution.get) if distribution else None
    coffee_share = f'{100 * distribution.get("coffee", 0) / votes_cast:.0f}%' if votes_cast else "—"

    cards = [
        ("Registered users", user_count),
        ("Rooms", room_count),
        ("Days with activity", summary["days_active"]),
        ("Rooms created", totals["rooms_created"]),
        ("Room joins", totals["joins"]),
        ("Rounds revealed", rounds),
        ("Auto-reveals", totals["auto_reveals"]),
        ("Votes cast", votes_cast),
        ("Avg. participants / round", avg_participants),
        ("Most popular card", _vote_label(favourite) if favourite else "—"),
        ("☕ share of votes", coffee_share),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="value">{html.escape(str(v))}</div>'
        f'<div class="label">{html.escape(label)}</div></div>'
        for label, v in cards
    )

    body = f"""
        <section class="cards">{cards_html}</section>
        <h2>Vote distribution</h2>
        {_bar_rows(_ordered_votes(distribution))}
        <h2>Last 30 active days</h2>
        {_days_table(summary["days"][:30])}
    """
    return _page("Analytics", body)


def _vote_label(value: str) -> str:
    return "☕" if value == "coffee" else value


def _ordered_votes(distribution: Dict[str, int]) -> List[tuple]:
    known = [(v, distribution.get(v, 0)) for v in VOTE_ORDER]
    extra = [(v, c) for v, c in distribution.items() if v not in VOTE_ORDER]
    return [(_vote_label(v), c) for v, c in known + extra]


def _bar_rows(rows: List[tuple]) -> str:
    peak = max((c for _, c in rows), default=0) or 1
    return '<div class="bars">' + "".join(
        f'<div class="bar-row"><span class="bar-label">{html.escape(str(label))}</span>'
        f'<span class="bar"><span style="width:{100 * count / peak:.1f}%"></span></span>'
        f'<span class="bar-count">{count}</span></div>'
        for label, count in rows
    ) + "</div>"


def _days_table(days: List[dict]) -> str:
    if not days:
        return "<p class='muted'>No activity recorded yet.</p>"
    peak = max(d["active_users"] for d in days) or 1
    rows = "".join(
        f"<tr><td>{html.escape(d['date'])}</td>"
        f"<td><span class='bar inline'><span style='width:{100 * d['active_users'] / peak:.1f}%'></span></span>"
        f" {d['active_users']}</td>"
        f"<td>{d['joins']}</td><td>{d['rooms_created']}</td><td>{d['rounds_revealed']}</td>"
        f"<td>{d['votes_cast']}</td><td>{d['peak_room_size']}</td></tr>"
        for d in days
    )
    return (
        "<table><thead><tr><th>Date</th><th>Active users</th><th>Joins</th><th>Rooms created</th>"
        "<th>Rounds</th><th>Votes</th><th>Largest room</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _page(title: str, body: str) -> web.Response:
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BingoPoker {title}</title>
<link rel="icon" type="image/png" href="/imgs/favicon.png">
<style>
  :root {{ --bg:#0f1720; --surface:#16212c; --border:#26394a; --text:#e6edf3; --muted:#8aa0b4; --primary:#057FA8; --primary-light:#0aa8d8; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; padding:24px 16px; background:var(--bg); color:var(--text); font-family: system-ui, sans-serif; }}
  main {{ max-width:1100px; margin:0 auto; }}
  header {{ display:flex; gap:16px; align-items:baseline; flex-wrap:wrap; margin-bottom:20px; }}
  header h1 {{ margin:0; font-size:22px; color:var(--primary-light); }}
  header a {{ color:var(--muted); text-decoration:none; }}
  header a.current {{ color:var(--text); font-weight:600; }}
  h2 {{ font-size:14px; text-transform:uppercase; letter-spacing:.5px; color:var(--muted); margin:28px 0 10px; }}
  .muted {{ color:var(--muted); }}
  .files {{ display:flex; gap:6px; flex-wrap:wrap; margin-bottom:12px; }}
  .files a {{ padding:4px 10px; border:1px solid var(--border); border-radius:6px; color:var(--text); text-decoration:none; font-size:13px; }}
  .files a.active {{ background:var(--primary); border-color:var(--primary); }}
  pre {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:12px; overflow:auto; font-size:12px; line-height:1.45; max-height:75vh; white-space:pre-wrap; word-break:break-word; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(160px, 1fr)); gap:10px; }}
  .card {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:14px; }}
  .card .value {{ font-size:24px; font-weight:700; }}
  .card .label {{ font-size:12px; color:var(--muted); margin-top:4px; }}
  .bars {{ display:flex; flex-direction:column; gap:6px; max-width:600px; }}
  .bar-row {{ display:grid; grid-template-columns:48px 1fr 48px; gap:10px; align-items:center; font-size:13px; }}
  .bar-label {{ text-align:right; }}
  .bar {{ display:block; height:14px; background:var(--surface); border-radius:4px; overflow:hidden; }}
  .bar.inline {{ display:inline-block; width:80px; vertical-align:middle; }}
  .bar > span {{ display:block; height:100%; background:var(--primary); }}
  .bar-count {{ color:var(--muted); }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--border); white-space:nowrap; }}
  th {{ color:var(--muted); font-weight:500; }}
  .table-wrap {{ overflow-x:auto; }}
</style>
</head>
<body>
<main>
  <header>
    <h1>BingoPoker</h1>
    <a href="/logs" class="{"current" if title == "Logs" else ""}">Logs</a>
    <a href="/analytics" class="{"current" if title == "Analytics" else ""}">Analytics</a>
    <a href="/">Back to app</a>
  </header>
  <div class="table-wrap">{body}</div>
</main>
</body>
</html>"""
    return web.Response(text=page, content_type="text/html")


def setup_admin_routes(app: web.Application) -> None:
    """Register the password-protected admin pages."""
    app.router.add_get("/logs", require_admin(logs_handler))
    app.router.add_get("/analytics", require_admin(analytics_handler))
