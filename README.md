# BingoPoker - Agile Scrum Poker with Bingo Cards

## Overview

BingoPoker is a collaborative web-based application designed for agile teams during sprint refinement sessions. It combines the power of planning poker (Fibonacci estimation) with an interactive 5x5 bingo card, allowing teams to visualize story points while identifying consensus and outliers in real-time.

## Features

### Core Features
- **Configurable Bingo Card**: 5x5 grid using the built-in default, a custom grid, or an imported JSON file
- **Planning Poker**: Fibonacci scale (0, 1, 2, 3, 5, 8, 13, 21, Split) plus a default ☕ "no estimate" card
- **Real-time Collaboration**: WebSocket sessions keep every participant in sync
- **Worker / Observer Roles**: Switchable at any time; an observer's bingo picks are always visible, a worker's stay hidden until reveal
- **Color-coded Users**: Each participant gets a color from a 10-color palette for easy identification
- **Persistent Rooms**: Room configurations are saved and reusable after everyone leaves
- **Creator-only Room Removal**: Only the user who created a room can delete it
- **Config Export/Import**: Download a room's grid as JSON and reuse it when creating another room
- **Shareable Room Links**: `?r=<room_id>` deep links prompt for login and then auto-join
- **Build Version**: The room list shows the running version and build date
- **Admin Pages**: Password-protected `/logs` (log viewer) and `/analytics` (usage statistics), enabled by `ADMIN_PASSWORD`

### Session Features
- **Bingo Card Selection**: Click cells to flag the difficulties a task involves
- **Poker Selection**: Everyone starts on ☕; choose a story point estimate (an explicit ☕ counts too) and others only see "voted" or "waiting"
- **Ready Toggle**: A green Ready button under the estimate puts a green ✓ next to your name for everyone, so the team can see when all are done; click again to undo
- **Reveal Mechanism**: Votes stay hidden until someone reveals, then the average (☕ votes excluded) and split count are shown
- **Auto-reveal**: A room-wide checkbox under Reveal All reveals the round automatically as soon as every participant is ready
- **Reset Functionality**: Start a new round without losing the room configuration

### Privacy
- Emails are never written to disk in plain text. `users.json` is keyed by a random user ID and stores an HMAC-SHA256 email digest.
- Application logs reference user IDs only.
- Analytics store daily aggregate counters only; the current day's random user IDs are kept just to count unique users and are dropped when the day ends.

### Known Limits
- Selections are in-memory only and are lost when the last participant leaves a room or the server restarts (including container updates)
- Room configurations persist indefinitely
- Colors repeat after 10 participants; there is no hard participant limit
- No password authentication — identity is email plus username

## Project Structure

```
BingoPoker/
├── docs/
│   ├── README.md                 # This file
│   ├── ARCHITECTURE.md           # System design and component overview
│   ├── DATA_STRUCTURES.md        # JSON schemas and data formats
│   ├── USER_FLOW.md              # Step-by-step user interaction flow
│   ├── API_SPECIFICATIONS.md     # REST endpoints and WebSocket messages
│   ├── DEVELOPMENT.md            # Setup and development guide
│   ├── CODING_RULES.md           # Conventions this codebase follows
│   ├── IMPLEMENTATION_TASKS.md   # Build status and outstanding work
│   └── STARTUP.md                # Deployment and hosting guide
│
├── backend/
│   ├── app.py                # aiohttp app factory, routes, startup, logging
│   ├── utils/
│   │   ├── room_manager.py       # Room config persistence + session state
│   │   ├── user_manager.py       # User registration, email hashing, persistence
│   │   ├── analytics_manager.py  # Daily usage counters (analytics.json)
│   │   ├── file_io.py            # Crash-safe atomic JSON/text writes
│   │   ├── color_palette.py      # 10-color palette assignment
│   │   └── validators.py         # Input validation helpers
│   ├── routes/
│   │   ├── users.py              # POST/GET/PUT /api/user
│   │   ├── rooms.py              # POST/GET/DELETE /api/room, GET /api/rooms
│   │   ├── admin.py              # Password-protected /logs and /analytics pages
│   │   └── debug.py              # DEBUG ONLY: delete-all endpoints
│   ├── handlers/
│   │   └── websocket.py          # WebSocket lifecycle and message handling
│   ├── tests/                # pytest suite (conftest.py fixtures + test_*.py)
│   ├── logs/                 # Default LOG_DIR (gitignored)
│   │   ├── bingopoker.log        # Today's application event log
│   │   └── bingopoker.log.YYYY-MM-DD  # Rotated at midnight, 30 files kept
│   └── data/
│       ├── users.json            # user_id → {email_hash, username, role}
│       ├── rooms.json            # room_id → config
│       ├── analytics.json        # Daily aggregate usage counters
│       └── .email_pepper         # Auto-generated hashing secret (gitignored)
│
├── requirements.txt          # Production Python dependencies
├── requirements-dev.txt      # Dev/test dependencies (pytest, pytest-aiohttp)
├── pytest.ini                # pytest config (testpaths, pythonpath, asyncio mode)
├── Dockerfile                # Production image
├── docker-compose.yml        # NAS deployment (app + Caddy + Watchtower)
├── .github/workflows/
│   └── docker.yml            # CI: run tests, then build and publish the image
│
└── frontend/
    ├── index.html            # Single-page app shell (login modal + 2 screens)
    ├── css/
    │   └── styles.css        # Dark theme, Outfit font, responsive layout
    ├── js/
    │   ├── app.js            # UI state, navigation, and WebSocket handling
    │   └── api.js            # REST API client + GridUtils constants
    └── templates/
        └── agile-default.json  # Sample grid file for the Import JSON option
```

## Tech Stack

### Backend
- **Framework**: Python 3 with aiohttp (REST + WebSocket)
- **Storage**: JSON files written asynchronously and atomically (temp file + `os.replace`)
- **Config**: python-dotenv (`HOST`, `PORT`, `DEBUG`, `DATA_DIR`, `LOG_DIR`, `EMAIL_HASH_PEPPER`, `ADMIN_PASSWORD`, `APP_VERSION`, `BUILD_DATE`)
- **Testing**: pytest + pytest-aiohttp; CI runs the suite before publishing the Docker image

### Frontend
- **Languages**: HTML5, CSS3, JavaScript (Vanilla, no build step)
- **Communication**: `fetch` for REST, native `WebSocket` for live updates
- **Styling**: Dark theme built on CSS custom properties

## Quick Start

See [STARTUP.md](docs/STARTUP.md) for detailed startup instructions.

```bash
# Install dependencies (one time, from the repo root)
pip3 install -r requirements.txt

# Run the server
cd backend
python3 app.py

# Run the tests (optional, from the repo root)
pip3 install -r requirements-dev.txt
pytest

# Open browser
http://localhost:8081
```

## User Journey

1. **First Visit**: Enter email, username, and role (Worker or Observer)
2. **Join Room**: Pick an existing room, create one, or open a shared `?r=` link
3. **Configure**: (Room creator) Use the default grid, build a custom one, or import JSON
4. **Play Round**:
   - Everyone marks the bingo cells that apply
   - Everyone picks a poker value (☕ by default)
   - Everyone clicks Ready when done; a green ✓ appears next to their name
   - Anyone clicks Reveal, or the round reveals itself once everyone is ready if Auto-reveal is ticked
   - All selections become visible, with the average and split count
5. **Review**: Discuss consensus and outliers
6. **Reset**: Clear selections and ready ticks for the next round

## Key Design Decisions

- **Real-time WebSocket**: Instant updates across all participants
- **Local JSON Storage**: Simple persistence without a database
- **Hashed Emails**: Identity is verifiable without storing personal data
- **Color-coded Visibility**: Participants instantly recognize each other's selections
- **Persistent Rooms**: Configurations are reusable across sessions
- **Hidden Votes Until Reveal**: Prevents anchoring bias in estimations
- **Asymmetric Role Visibility**: Observers surface scope early, workers stay unbiased

## File Documentation

- [STARTUP.md](docs/STARTUP.md) - How to launch the app (shared hosting & local)
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System components and data flow
- [DATA_STRUCTURES.md](docs/DATA_STRUCTURES.md) - JSON schemas and file formats
- [USER_FLOW.md](docs/USER_FLOW.md) - Detailed interaction flows
- [API_SPECIFICATIONS.md](docs/API_SPECIFICATIONS.md) - REST endpoints and WebSocket messages
- [DEVELOPMENT.md](docs/DEVELOPMENT.md) - Development setup, automated tests and manual test guide
- [CODING_RULES.md](docs/CODING_RULES.md) - Conventions this codebase follows
- [IMPLEMENTATION_TASKS.md](docs/IMPLEMENTATION_TASKS.md) - Build status and outstanding work

---

*Last Updated: 2026-10-07*
