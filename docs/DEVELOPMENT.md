# Development Guide - BingoPoker

## Quick Start

### Prerequisites
- Python 3.9+ (CI and the Docker image use 3.12)
- pip
- A modern browser (Chrome, Firefox, Safari, Edge)

### Setup

```bash
# 1. Open the project
cd /path/to/BingoPoker

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS/Linux

# 3. Install runtime + test dependencies (requirements-dev.txt includes requirements.txt)
pip install -r requirements-dev.txt

# 4. Copy the environment template
copy .env.example .env         # Windows
cp .env.example .env           # macOS/Linux

# 5. Run the server from the backend directory
cd backend
python app.py
```

The server prints `Starting BingoPoker on 0.0.0.0:8081`. Open <http://localhost:8081>.

> Run `python app.py` from `backend/`, not from the repository root — imports such as
> `from utils.user_manager import UserManager` are resolved relative to that directory.

---

## Project Structure

```
BingoPoker/
├── .env.example                 # Environment template
├── README.md                    # Project overview
├── ARCHITECTURE.md              # System design
├── DATA_STRUCTURES.md           # JSON schemas
├── USER_FLOW.md                 # User interactions
├── API_SPECIFICATIONS.md        # REST and WebSocket API
├── CODING_RULES.md              # Conventions
├── IMPLEMENTATION_TASKS.md      # Implementation status
├── DEVELOPMENT.md               # This file
├── STARTUP.md                   # Run instructions
├── requirements.txt             # Runtime dependencies
├── requirements-dev.txt         # Test dependencies (includes requirements.txt)
├── pytest.ini                   # pytest config (testpaths, pythonpath, asyncio mode)
├── Dockerfile / docker-compose.yml
├── .github/workflows/docker.yml # CI: test job, then build-and-publish
│
├── backend/
│   ├── app.py                   # aiohttp app factory + entry point
│   ├── routes/
│   │   ├── users.py             # /api/user endpoints
│   │   ├── rooms.py             # /api/room, /api/rooms endpoints
│   │   ├── admin.py             # /logs, /analytics (only mounted when ADMIN_PASSWORD is set)
│   │   └── debug.py             # /api/debug/* (only mounted when DEBUG=true)
│   ├── handlers/
│   │   └── websocket.py         # /ws/{room_id}/{user_email} handler
│   ├── utils/
│   │   ├── user_manager.py      # User registration + hashed-email persistence
│   │   ├── room_manager.py      # Room config persistence + in-memory sessions
│   │   ├── analytics_manager.py # Daily usage counters (analytics.json)
│   │   ├── file_io.py           # Atomic JSON/text writes
│   │   ├── color_palette.py     # 10-color palette
│   │   └── validators.py        # Input validation
│   ├── data/
│   │   ├── users.json           # User registry (persistent)
│   │   ├── rooms.json           # Room configs (persistent)
│   │   ├── analytics.json       # Daily usage counters (persistent)
│   │   └── .email_pepper        # Auto-generated HMAC pepper (secret)
│   ├── logs/
│   │   ├── bingopoker.log       # Today's application log
│   │   └── bingopoker.log.YYYY-MM-DD  # Rotated daily, 30 files kept
│   └── tests/
│       ├── conftest.py          # Fixtures: app via create_app() with temp data/log dirs
│       ├── test_validators.py
│       ├── test_room_manager.py
│       ├── test_file_io.py
│       ├── test_analytics_manager.py
│       ├── test_websocket.py    # End-to-end WebSocket protocol
│       └── test_app.py          # Health/version, privacy, log rotation, admin pages
│
└── frontend/
    ├── index.html               # All screens in one document
    ├── css/styles.css           # All styles, theme via :root variables
    ├── js/
    │   ├── api.js               # REST client + GridUtils (default grid, helpers)
    │   └── app.js               # State, screens, rendering, WebSocket handling
    └── templates/
        └── agile-default.json   # Importable grid template
```

---

## Dependencies

### Backend runtime (`requirements.txt`, repo root)

```
aiohttp>=3.9.0
aiofiles>=23.2.0
python-dotenv>=1.0.0
```

- `aiohttp` — async web framework with native WebSocket support
- `aiofiles` — async file I/O for JSON persistence
- `python-dotenv` — loads `.env`

### Backend dev/test (`requirements-dev.txt`, repo root)

```
-r requirements.txt
pytest>=8.0
pytest-aiohttp>=1.0
```

Install with `pip install -r requirements-dev.txt`. See [Testing](#testing).

### Frontend
Pure HTML5, CSS3 and vanilla JavaScript. No build step, no framework, no npm.

---

## Configuration

All configuration is read in `backend/app.py` and `backend/utils/user_manager.py`.
Copy `.env.example` to `.env` and adjust.

| Variable | Default | Meaning |
|---|---|---|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8081` | Bind port |
| `DEBUG` | `False` | When `true`, mounts the debug routes |
| `DATA_DIR` | `backend/data` | Where `users.json`, `rooms.json`, `analytics.json` and `.email_pepper` live |
| `LOG_DIR` | `backend/logs` | Where `bingopoker.log` and its rotated files live |
| `EMAIL_HASH_PEPPER` | *(unset)* | HMAC pepper for email hashing |
| `ADMIN_PASSWORD` | *(unset)* | When set, mounts the `/logs` and `/analytics` admin pages |
| `APP_VERSION` | `dev` | Build version shown in the app; set by CI at image build time |
| `BUILD_DATE` | *(unset)* | Build timestamp shown in the app; set by CI at image build time |

Notes:
- `DEBUG` is truthy only for the literal string `true` (case-insensitive).
- A relative `DATA_DIR` is resolved against the working directory, so prefer an absolute path.
- When `EMAIL_HASH_PEPPER` is unset, a random pepper is generated once and stored in
  `<DATA_DIR>/.email_pepper`. Changing or losing that value orphans every existing user
  record, because emails are stored only as HMAC-SHA256 digests and cannot be recovered.

---

## Backend Overview

Rather than duplicating source here, this section points at the module that owns each concern.

| Concern | Module |
|---|---|
| App factory, logging setup, static file mounts | `backend/app.py` |
| User registration, hashed-email lookup, role/username updates | `backend/utils/user_manager.py` |
| Room config persistence, session state, selections, reveal/reset | `backend/utils/room_manager.py` |
| Per-session color assignment | `backend/utils/color_palette.py` |
| Input validation | `backend/utils/validators.py` |
| Daily usage statistics | `backend/utils/analytics_manager.py` |
| Atomic JSON/text file writes | `backend/utils/file_io.py` |
| REST handlers | `backend/routes/users.py`, `backend/routes/rooms.py` |
| Admin pages (`/logs`, `/analytics`) | `backend/routes/admin.py` |
| Real-time session handling | `backend/handlers/websocket.py` |

Key facts to keep in mind while working in the backend:

- `create_app(data_dir=None, log_dir=None, admin_password=None)` builds the app; the
  arguments override `DATA_DIR`, `LOG_DIR` and `ADMIN_PASSWORD` (the tests use them).
- Managers are created in `startup_handler` and stored on the app as
  `app["user_manager"]` / `app["room_manager"]` / `app["analytics_manager"]`.
- Every JSON write goes through `write_json_atomic` in `utils/file_io.py`.
- Room configuration is persisted to `rooms.json`; session state (`users`,
  `bingo_selections`, `poker_selections`, `ready`, `revealed`, `color_counter`) is in memory only
  and is lost on restart.
- `users.json` is keyed by a random `uuid4().hex` user ID and stores an `email_hash`,
  never the plain email. `rooms.json` stores `created_by` as a user ID.
- `ColorPalette` exposes a single method, `get_color_by_index(index)`, over a 10-color
  list. A room's `color_counter` increments monotonically, so colors repeat once more than
  10 participants have joined that session.
- Validators return `(is_valid, error_message)`; managers return `(success, error)` or
  `(success, error, data)`.
- Grids are always 5×5 strings. The centre cell (2,2) is styled differently but has no
  special game meaning. Poker values are `coffee` (☕, the default, excluded from the average), `0, 1, 2, 3, 5, 8, 13, 21, split`.
- Usernames are 1–50 characters, room names 1–100 characters, room IDs match
  `room-XXXXXXXX`. There is no cap on participants per room.

---

## Frontend Overview

`frontend/index.html` contains every screen (login modal, room select, game screen) and
switches them via the `.screen.active` class.

`frontend/js/api.js` exposes:
- `BingoPokerAPI` — static methods wrapping the REST endpoints, each returning
  `{ success, data }` or `{ success, error }`.
- `GridUtils` — `DEFAULT_GRID`, `createEmptyGrid()`, `isCenterCell(row, col)`,
  `isValidGrid(grid)`.

`frontend/js/app.js` holds the remaining logic in one module:
- `appState` — current user, current room, grid, selections, active WebSocket.
- Auth flow: `checkAuthStatus`, `handleRegister`, `handleLogout`, `handleRoleSwap`.
  The user profile is cached in `localStorage` under `bingopoker_user`.
- Room flow: `loadRooms`, `handleCreateRoom`, `joinRoom`, `handleDeleteRoom`,
  `handleLeaveRoom`, `handleDownloadGrid`.
- Grid editor: `useDefaultTemplate`, `useEmptyTemplate`, `importGridJSON`,
  `handleGridFileImport`, `renderGridEditor`.
- Rendering: `renderBingoGrid` (builds cells once via `buildBingoGrid`, then updates them in
  place), `renderPokerValues`, `renderReadyButton`, `renderUsers`, `renderRoundControls`.
- WebSocket: `connectWebSocket`, `wsSend`, `handleWsMessage`.

Visibility rule implemented in `renderBingoGrid`: an observer's bingo dots are always
visible to everyone; a worker's dots are visible only to that worker until the round is
revealed. Poker values render as `waiting`/`voted` before reveal and as the actual value
(☕ for anyone who chose it or never voted) plus an average summary after. Ready users get a green
✓ next to their name, visible to everyone.

Deep links use `?r=<room_id>`. If the visitor is not logged in, the room ID is stored in
`sessionStorage` under `pending_room` and joined right after registration.

### CSS
Theme colors and spacing live in the `:root` block of `frontend/css/styles.css`. The
`Responsive` section at the end holds the phone layout: below 768px wide, or under 500px tall
(phones in landscape), the fixed-height desktop layout becomes one scrolling column.
`index.html` links assets with a `?v=` cache-busting query string — bump it when shipping
CSS/JS changes.

---

## Testing

### Automated tests

The pytest suite lives in `backend/tests/`. Run it from the repository root:

```bash
pip install -r requirements-dev.txt
pytest
```

`pytest.ini` sets `testpaths = backend/tests`, `pythonpath = backend` (so `utils`,
`routes` and `handlers` import as in the app) and `asyncio_mode = auto`.

- `conftest.py` — a `client` fixture that builds the app with
  `create_app(data_dir=..., log_dir=..., admin_password=...)` on temporary directories, so
  tests never touch `backend/data` or `backend/logs`; plus helpers for registering
  synthetic users and creating rooms.
- `test_validators.py`, `test_room_manager.py`, `test_file_io.py`,
  `test_analytics_manager.py` — unit tests.
- `test_websocket.py` — end-to-end WebSocket protocol: join, selections, hidden votes,
  ready, auto-reveal, reset, broadcast pruning of failing sockets, analytics recording.
- `test_app.py` — health/version, no plain emails on disk, log rotation config, admin
  auth, `/logs` path traversal, `/analytics` page.

CI (`.github/workflows/docker.yml`) runs the same `pytest` in a `test` job on every push
to `main`; the Docker image is only built and published if it passes.

### Manual checks

UI behaviour is still verified manually:

1. Start the server and open <http://localhost:8081>.
2. Register a user, create a room from the default template, and join it.
3. In a second browser profile or private window, register a second user, join via the
   shared `?r=` link, and confirm both participants appear with distinct colors.
4. Make bingo and poker selections in both windows and confirm hidden-until-reveal
   behaviour for workers and always-visible behaviour for observers.
5. Hover a bingo cell in one window while the other window clicks cells; the hovered
   cell's border must not re-animate.
6. Click Ready in one window and confirm the green ✓ appears next to that name in both
   windows; click again and confirm it disappears.
7. Tick Auto-reveal, mark both users ready, and confirm the round reveals by itself
   once the second user is ready; reset and confirm the checkbox stays ticked.
8. Have one user click ☕ (they should show as voted), reveal, and check ☕ is shown and excluded from the
   average, then reset and confirm ticks and votes are cleared.
9. Confirm the room list shows "Development build" at the bottom of the info block.
10. In DevTools device mode at phone size (e.g. 384×832 portrait and 832×384 landscape),
    check the room list and game screen: no sideways scrolling, a square bingo grid that fits
    the screen, and Your Estimate / Ready directly below the grid.
11. Watch `backend/logs/bingopoker.log` and the browser console/network tab for errors.

---

## Debugging

### Logs
`backend/app.py` configures logging on startup:
- File handler at `<LOG_DIR>/bingopoker.log` (default `backend/logs`, level `INFO`,
  directory created automatically). It rotates at midnight to
  `bingopoker.log.YYYY-MM-DD` and keeps 30 files; days without log lines produce no file.
- Console handler at level `WARNING`, so the terminal stays quiet during normal use.
- `aiohttp.access` is raised to `WARNING` so request URLs — which contain emails — are not
  written to the log.

Log lines identify users by `user_id` and username. **Never add a log statement that
writes an email address.**

### Admin pages
Set `ADMIN_PASSWORD=<password>` (for example in your local `.env`) and restart to enable
<http://localhost:8081/logs> and <http://localhost:8081/analytics>. The browser asks for
HTTP Basic credentials: any username, the configured password. Without the variable the
server logs a warning at startup and both paths return 404.

### Debug endpoints
When `DEBUG=true`, `backend/routes/debug.py` is mounted and exposes two destructive
endpoints:

- `DELETE /api/debug/users` — clears `users.json` and the in-memory user index
- `DELETE /api/debug/rooms` — clears `rooms.json`, in-memory rooms and all sessions

They are not registered at all when `DEBUG` is false.

Add `?dev=true` to the frontend URL (for example <http://localhost:8081/?dev=true>) to
unhide the "Delete all users" / "Delete all rooms" buttons that call them.

### Browser DevTools
- **Console** — JavaScript errors and the `console.error` output from `api.js`/`app.js`.
- **Network → WS** — inspect WebSocket frames (`room_state`, `user_joined`,
  `bingo_updated`, `poker_updated`, `ready_updated`, `auto_reveal_updated`, `revealed`, `round_reset`, `replaced`,
  `user_left`).
- **Application → Local Storage** — inspect or clear `bingopoker_user`.

---

## Common Issues & Solutions

### Port already in use
```bash
netstat -ano | findstr :8081     # Windows
lsof -i :8081                    # macOS/Linux
```
Or set `PORT=8082` in `.env`.

### WebSocket closes immediately
The handler returns 401 if the email is not a registered user and 404 if the room does not
exist. Verify the account still exists (the debug endpoints may have wiped it) and that
the room ID is valid.

### "You joined this room from another tab or window."
Expected. A second connection for the same user and room closes the first one and sends a
`replaced` message.

### Participants and colors reset after a restart
Expected. Session state is in memory only; only room configs, user records and analytics
persist.

### All users are unknown after changing the pepper
Changing `EMAIL_HASH_PEPPER` (or deleting `backend/data/.email_pepper`) invalidates every
stored email digest. Restore the old value or re-register.

---

## Data Backup

```bash
# Windows
xcopy /E /I backend\data backend\data.backup

# macOS/Linux
cp -r backend/data backend/data.backup.$(date +%Y%m%d)
```

Include `.email_pepper` in any backup — without it the user records are unusable.

---

*Last Updated: 2026-10-07*
