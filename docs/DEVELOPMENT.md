# Development Guide - BingoPoker

## Quick Start

### Prerequisites
- Python 3.8+
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

# 3. Install runtime dependencies
pip install -r backend/requirements.txt

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
│
├── backend/
│   ├── app.py                   # aiohttp app factory + entry point
│   ├── requirements.txt         # Runtime dependencies
│   ├── requirements-dev.txt     # Test dependencies (currently unused)
│   ├── routes/
│   │   ├── users.py             # /api/user endpoints
│   │   ├── rooms.py             # /api/room, /api/rooms endpoints
│   │   └── debug.py             # /api/debug/* (only mounted when DEBUG=true)
│   ├── handlers/
│   │   └── websocket.py         # /ws/{room_id}/{user_email} handler
│   ├── utils/
│   │   ├── user_manager.py      # User registration + hashed-email persistence
│   │   ├── room_manager.py      # Room config persistence + in-memory sessions
│   │   ├── color_palette.py     # 10-color palette
│   │   └── validators.py        # Input validation
│   ├── data/
│   │   ├── users.json           # User registry (persistent)
│   │   ├── rooms.json           # Room configs (persistent)
│   │   └── .email_pepper        # Auto-generated HMAC pepper (secret)
│   ├── logs/
│   │   └── bingopoker.log       # Application log
│   └── tests/
│       └── __init__.py          # Empty — no tests exist yet
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

### Backend runtime (`backend/requirements.txt`)

```
aiohttp>=3.9.0
aiofiles>=23.2.0
python-dotenv>=1.0.0
```

- `aiohttp` — async web framework with native WebSocket support
- `aiofiles` — async file I/O for JSON persistence
- `python-dotenv` — loads `.env`

### Backend dev/test (`backend/requirements-dev.txt`)

```
pytest>=7.4.0
pytest-aiohttp>=1.1.0
```

Install separately with `pip install -r backend/requirements-dev.txt`.
See [Testing](#testing) — these are declared for future use but currently unused.

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
| `DATA_DIR` | `backend/data` | Where `users.json`, `rooms.json` and `.email_pepper` live |
| `EMAIL_HASH_PEPPER` | *(unset)* | HMAC pepper for email hashing |

Notes:
- `DEBUG` is truthy only for the literal string `true` (case-insensitive).
- A relative `DATA_DIR` is resolved against `app.py`'s directory, not the working directory.
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
| REST handlers | `backend/routes/users.py`, `backend/routes/rooms.py` |
| Real-time session handling | `backend/handlers/websocket.py` |

Key facts to keep in mind while working in the backend:

- Managers are created in `startup_handler` and stored on the app as
  `app["user_manager"]` / `app["room_manager"]`.
- Room configuration is persisted to `rooms.json`; session state (`users`,
  `bingo_selections`, `poker_selections`, `revealed`, `color_counter`) is in memory only
  and is lost on restart.
- `users.json` is keyed by a random `uuid4().hex` user ID and stores an `email_hash`,
  never the plain email. `rooms.json` stores `created_by` as a user ID.
- `ColorPalette` exposes a single method, `get_color_by_index(index)`, over a 10-color
  list. A room's `color_counter` increments monotonically, so colors repeat once more than
  10 participants have joined that session.
- Validators return `(is_valid, error_message)`; managers return `(success, error)` or
  `(success, error, data)`.
- Grids are always 5×5 strings. The centre cell (2,2) is styled differently but has no
  special game meaning. Poker values are `0, 1, 2, 3, 5, 8, 13, 21, split`.
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
- Rendering: `renderBingoGrid`, `renderPokerValues`, `renderUsers`, `renderRoundControls`.
- WebSocket: `connectWebSocket`, `wsSend`, `handleWsMessage`.

Visibility rule implemented in `renderBingoGrid`: an observer's bingo dots are always
visible to everyone; a worker's dots are visible only to that worker until the round is
revealed. Poker values render as `waiting`/`ready` before reveal and as the actual value
plus an average summary after.

Deep links use `?r=<room_id>`. If the visitor is not logged in, the room ID is stored in
`sessionStorage` under `pending_room` and joined right after registration.

### CSS
Theme colors and spacing live in the `:root` block of `frontend/css/styles.css`.
`index.html` links assets with a `?v=` cache-busting query string — bump it when shipping
CSS/JS changes.

---

## Testing

**There are currently no automated tests.** `backend/tests/` contains only an empty
`__init__.py`, and `pytest` / `pytest-aiohttp` are declared in
`backend/requirements-dev.txt` but nothing imports or runs them. Running `pytest` collects
zero tests.

Until a suite exists, verification is manual:

1. Start the server and open <http://localhost:8081>.
2. Register a user, create a room from the default template, and join it.
3. In a second browser profile or private window, register a second user, join via the
   shared `?r=` link, and confirm both participants appear with distinct colors.
4. Make bingo and poker selections in both windows and confirm hidden-until-reveal
   behaviour for workers and always-visible behaviour for observers.
5. Reveal, check the average summary, then reset.
6. Watch `backend/logs/bingopoker.log` and the browser console/network tab for errors.

---

## Debugging

### Logs
`backend/app.py` configures logging on startup:
- File handler at `backend/logs/bingopoker.log` (level `INFO`, directory created
  automatically).
- Console handler at level `WARNING`, so the terminal stays quiet during normal use.
- `aiohttp.access` is raised to `WARNING` so request URLs — which contain emails — are not
  written to the log.

Log lines identify users by `user_id` and username. **Never add a log statement that
writes an email address.**

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
  `bingo_updated`, `poker_updated`, `revealed`, `round_reset`, `replaced`, `user_left`).
- **Application → Local Storage** — inspect or clear `bingopoker_user`.

---

## Common Issues & Solutions

### Port already in use
```bash
netstat -ano | findstr :8081     # Windows
lsof -i :8081                    # macOS/Linux
```
Or set `PORT=8082` in `.env`.

### `ModuleNotFoundError: No module named 'utils'`
You ran `python backend/app.py` from the repository root. `cd backend` first.

### WebSocket closes immediately
The handler returns 401 if the email is not a registered user and 404 if the room does not
exist. Verify the account still exists (the debug endpoints may have wiped it) and that
the room ID is valid.

### "You joined this room from another tab or window."
Expected. A second connection for the same user and room closes the first one and sends a
`replaced` message.

### Participants and colors reset after a restart
Expected. Session state is in memory only; only room configs and user records persist.

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

*Last Updated: 2026-08-18*
