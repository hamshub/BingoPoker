# Architecture Document - BingoPoker

## System Overview

BingoPoker is a real-time collaborative web application using a client-server WebSocket architecture. A single aiohttp process serves the static frontend, the REST API, and the WebSocket endpoint. Room configuration is persisted to JSON on disk; live round state is kept in memory only.

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser Clients                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Client 1 │  │ Client 2 │  │ Client 3 │  │ Client N │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼───────────┘
        │             │             │             │
        └─────────────┼─────────────┼─────────────┘
                      │ REST + WebSocket
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼──────────────────────────▼─────────┐
│         aiohttp Server (Python 3)          │
├────────────────────────────────────────────┤
│  ┌──────────────────────────────────────┐  │
│  │  handlers/websocket.py               │  │
│  │  - Connection registry per room      │  │
│  │  - Message routing                   │  │
│  │  - Broadcast logic                   │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │  routes/users.py, routes/rooms.py    │  │
│  │  routes/debug.py (DEBUG only)        │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │  utils/room_manager.py               │  │
│  │  - Room creation/deletion            │  │
│  │  - In-memory session state           │  │
│  │  - Bingo + Poker selection tracking  │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │  utils/user_manager.py               │  │
│  │  - Registration, hashed email store  │  │
│  │  - Username / role updates           │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │  utils/color_palette.py, validators  │  │
│  └──────────────────────────────────────┘  │
└──────────────┬──────────────────────────┬──┘
               │                          │
               ▼                          ▼
        ┌─────────────┐          ┌─────────────┐
        │  users.json │          │ rooms.json  │
        │ (Persistent)│          │(Persistent) │
        └─────────────┘          └─────────────┘
```

## Component Details

### 1. Frontend (Client-Side)

Static HTML/CSS/vanilla JavaScript, served by the same aiohttp app. There is no build step and no framework.

#### Files
- `index.html` - Login modal overlay plus two screens: `roomSelectScreen` and `gameScreen`
- `js/api.js` - REST client class `BingoPokerAPI` (`registerUser`, `getUser`, `updateRole`, `createRoom`, `getRoom`, `listRooms`, `deleteRoom`) and the `GridUtils` object (`DEFAULT_GRID`, `createEmptyGrid`, `isCenterCell`, `isValidGrid`)
- `js/app.js` - All application state (`appState`), screen navigation, rendering, and the WebSocket client
- `css/styles.css` - Dark theme styling (Outfit font, `#057FA8` accent palette)
- `templates/agile-default.json` - Sample grid file users can import when creating a room

#### Responsibilities
- User input handling (bingo cell toggle, poker value selection, round controls)
- WebSocket connection lifecycle (no automatic reconnection is implemented)
- Real-time UI updates based on server messages
- Local user profile caching (`localStorage` key `bingopoker_user`)
- Applying the selection visibility rules when rendering (see [Visibility Model](#visibility-model))
- Escaping all user-supplied text before inserting it into HTML (`escapeHtml`)
- Visual rendering of:
  - Bingo card grid with per-user color dots
  - Participant list with colors, role badges, and vote status
  - Poker value buttons and the post-reveal average / split summary
  - Room information and shareable invite link

### 2. Backend (Server-Side)

#### Main Application (`app.py`)
Exposes `create_app()` plus the lifecycle and simple request handlers:
- `startup_handler` - configures logging, instantiates `UserManager` and `RoomManager`, loads both from disk, and runs `room_manager.migrate_creator_ids(...)` to convert legacy plain-email `created_by` values into user IDs
- `cleanup_handler` - logs shutdown
- `health_check_handler` - `GET /health`
- `serve_index_handler` - `GET /` serves `frontend/index.html`

Registered routes:
- `GET /` and `GET /health`
- User routes from `routes/users.py`
- Room routes from `routes/rooms.py`
- Debug routes from `routes/debug.py` — **only when `DEBUG=true`**
- `GET /ws/{room_id}/{user_email}` → `room_websocket_handler`
- Static directories `/css`, `/js`, `/templates`

Configuration comes from environment variables (`.env` supported via `python-dotenv`): `HOST`, `PORT` (default `8081`), `DEBUG`, `DATA_DIR`, `EMAIL_HASH_PEPPER`. Logging writes to `backend/logs/bingopoker.log` (INFO) and the console (WARNING and above); aiohttp access logs are suppressed so URLs containing emails are never written.

#### User Routes (`routes/users.py`)
- `register_user_handler` — `POST /api/user`
- `get_user_handler` — `GET /api/user/{email}`
- `update_user_handler` — `PUT /api/user/{email}` (username and/or role)

#### Room Routes (`routes/rooms.py`)
- `create_room_handler` — `POST /api/room` (duplicate room names rejected with `409`)
- `get_room_handler` — `GET /api/room/{room_id}`
- `list_rooms_handler` — `GET /api/rooms`
- `delete_room_handler` — `DELETE /api/room/{room_id}` (creator only, `403` otherwise)

This module contains no WebSocket code.

#### Debug Routes (`routes/debug.py`)
Destructive development helpers, registered only when `DEBUG=true`:
- `DELETE /api/debug/users` — wipes `users.json` and the in-memory user index
- `DELETE /api/debug/rooms` — wipes `rooms.json` and all sessions

#### WebSocket Handler (`handlers/websocket.py`)
- `room_websocket_handler` — public entry point bound to `GET /ws/{room_id}/{user_email}`
- `_handle_message` — routes `bingo_select`, `poker_select`, `reveal`, `reset`
- `_broadcast` — sends to every open socket in a room, optionally excluding one email, and prunes dead sockets
- `_disconnect` — deregisters the socket, removes the user from the session, and broadcasts `user_left`
- `_serialize_session` — converts tuple cell coordinates to JSON-friendly lists
- `_connections` — module-level registry `{room_id: {email: ws}}`

#### Room Manager (`utils/room_manager.py`)
Manages persisted room config and in-memory session state:
- **Persisted room config** (`rooms.json`):
  - `room_id` (generated, `room-{8 alphanumeric}`)
  - `name` (display name)
  - `config.grid` (5x5 bingo card text)
  - `created_at`, `created_by` (creator's **user ID**, never an email)
- **Session** (in-memory, ephemeral, keyed separately by `room_id`):
  - `users` (current connections, each with assigned `color`)
  - `bingo_selections` (email → list of `(row, col)` tuples)
  - `poker_selections` (email → poker value)
  - `revealed` (boolean)
  - `color_counter` (monotonic, never reused within a room)

- **Methods**:
  - `load()` → read `rooms.json`, creating it if missing
  - `create_room(room_name, grid, created_by)` → (success, error, room_data)
  - `get_room(room_id)` → persisted config
  - `get_room_state(room_id)` → `{ config, session }`
  - `add_user_to_session(room_id, user_email, user_data)` → bool
  - `remove_user_from_session(room_id, user_email)` → bool; deletes the session when the last user leaves
  - `record_bingo_selection(room_id, user_email, cell_row, cell_col)` → (success, error) — toggles the cell
  - `record_poker_selection(room_id, user_email, value)` → (success, error)
  - `reveal_round(room_id)` → (success, error)
  - `reset_round(room_id)` → (success, error)
  - `get_active_rooms()` → all persisted room configs
  - `migrate_creator_ids(resolve_user_id)` → replaces legacy email `created_by` values with user IDs
  - `delete_room(room_id)` → (success, error)

#### User Manager (`utils/user_manager.py`)
Manages user profiles with privacy-preserving storage:
- **Stored record** (keyed by a random `uuid4().hex` user ID):
  - `user_id`
  - `email_hash` (HMAC-SHA256 digest of the normalized email)
  - `username`
  - `role` (`"worker"` or `"observer"`)
- **API-facing profile**: `user_id`, `username`, `role`, plus the `email` echoed back from the request

- **Methods**:
  - `load()` → read `users.json`, load/create the pepper, migrate legacy email-keyed records, rebuild the index
  - `hash_email(email)` → stable HMAC digest
  - `resolve_user_id(email)` → user ID or `None`
  - `register_user(email, username, role)` → (success, error, user_profile)
  - `get_user(email)` → public profile or `None`
  - `update_username(email, new_username)` → (success, error)
  - `update_role(email, new_role)` → (success, error)
  - `user_exists(email)` → boolean

#### Color Palette (`utils/color_palette.py`)
10-color palette with rolling assignment per room session:
- Predefined list of 10 maximally contrasted hex colors
- Exactly one method: `get_color_by_index(index)`, which wraps with modulo over the 10-color list
- Color assigned at join time using a monotonic per-room counter (1st join = color 0, 2nd = color 1, ...); rejoining users get the **next** color in sequence, not their original one
- There is no maximum number of participants — beyond 10 users in a room the colors simply repeat
- Color is ephemeral — never persisted to `users.json`

#### Validators (`utils/validators.py`)
Static helpers returning `(is_valid, error_message)`: `validate_email`, `validate_username` (1–50 chars), `validate_room_name` (1–100 chars), `validate_room_id` (`room-XXXXXXXX`), `validate_grid` (5×5 array of strings), `validate_poker_value` (`0, 1, 2, 3, 5, 8, 13, 21, split`).

### 3. Data Persistence

Room and user data are written asynchronously with `aiofiles` to JSON files under `backend/data`. Session and round state lives in memory only and is lost when the last user leaves a room or when the server restarts.

#### `users.json`
Keyed by a random user ID; the email exists only as a keyed HMAC digest.

```json
{
  "3f2a9c1d4b8e4f0aa1c7d5e6f8b90123": {
    "user_id": "3f2a9c1d4b8e4f0aa1c7d5e6f8b90123",
    "email_hash": "9c4f0a1b2c3d4e5f60718293a4b5c6d7e8f9012345678901234567890abcdef1",
    "username": "John Doe",
    "role": "worker"
  }
}
```

#### `rooms.json`
```json
{
  "room-abc123XY": {
    "room_id": "room-abc123XY",
    "name": "Sprint 42 Planning",
    "config": {
      "grid": [
        ["Story A", "Story B", "Story C", "Story D", "Story E"],
        ["Story F", "Story G", "Story H", "Story I", "Story J"],
        ["Story K", "Story L", "Story M", "Story N", "Story O"],
        ["Story P", "Story Q", "Story R", "Story S", "Story T"],
        ["Story U", "Story V", "Story W", "Story X", "Story Y"]
      ]
    },
    "created_at": "2026-08-12T10:00:00",
    "created_by": "3f2a9c1d4b8e4f0aa1c7d5e6f8b90123"
  }
}
```

#### `.email_pepper`
The HMAC pepper used to compute `email_hash`. Taken from the `EMAIL_HASH_PEPPER` environment variable when set; otherwise a random value is generated on first run and stored in `backend/data/.email_pepper`. Changing the pepper invalidates all existing email lookups.

## Privacy & Security Model

- **Emails are never stored in plain text.** `users.json` is keyed by a random `uuid4` hex user ID, and each record holds only an HMAC-SHA256 digest of the email. An in-memory index maps `email_hash → user_id`.
- **`rooms.json` stores `created_by` as a user ID**, not an email. Legacy records are migrated automatically at startup by `migrate_creator_ids`.
- Emails are still the API- and WebSocket-facing identifier (path parameters) and the in-memory session key — they are simply never written to disk or to logs. The aiohttp access logger is silenced for this reason.
- **Authorization**: only the room creator may delete a room; the server compares the requester's resolved user ID against `created_by` and returns `403` otherwise. This is the only authorization rule in the application — there is no password or token authentication.
- **Output encoding**: the frontend escapes all user-supplied text (usernames, room names, grid cells) before inserting it into HTML.

## Real-Time Model

One WebSocket per user per room: `GET /ws/{room_id}/{user_email}`.

- The handler returns `401` if the user is unknown and `404` if the room is unknown.
- On join the server adds the user to the session with the next palette color, sends `room_state` to the joiner, and broadcasts `user_joined` (full users list) to everyone else.
- Reconnecting the same email to the same room sends `replaced` to the previous socket and closes it.
- On disconnect the server removes the user from the session, broadcasts `user_left`, and deletes the session once the room is empty. Connection-reset errors are caught and logged, not raised.

### Message Types

Every message uses the envelope `{ "type": "...", "payload": { ... } }`.

| Direction | Type | Notes |
|---|---|---|
| Client → Server | `bingo_select` | `{ row, col }` — toggles the cell |
| Client → Server | `poker_select` | `{ value }` |
| Client → Server | `reveal` | Empty payload |
| Client → Server | `reset` | Empty payload |
| Server → Client | `room_state` | Sent only to the joining socket |
| Server → Client | `user_joined` | Full users list |
| Server → Client | `user_left` | Leaving email plus remaining users |
| Server → Client | `bingo_updated` | Full `bingo_selections` map |
| Server → Client | `poker_updated` | `{ email, has_selection }` — never the value |
| Server → Client | `revealed` | `bingo_selections` + `poker_selections` |
| Server → Client | `round_reset` | Empty payload |
| Server → Client | `replaced` | The previous socket for the same user is being closed |
| Server → Client | `error` | Invalid JSON or unknown message type |

Clients connect directly to `/ws/{room_id}/{user_email}` — there is no separate "join" message. See [API_SPECIFICATIONS.md](API_SPECIFICATIONS.md#websocket-messages) for the full payload shapes.

## Visibility Model

- **Worker bingo selections** are visible only to the selecting user until the round is revealed.
- **Observer bingo selections** are visible to everyone at all times.
- **Poker values** are never shown before reveal; other participants only see `ready` or `waiting`. The `poker_updated` broadcast deliberately omits the value.
- Bingo dot filtering is applied by the client in `renderBingoGrid()`, using each session user's `role` and the current `revealed` flag.

## Data Flow Sequences

### Initial Room Load
```
Client → GET /api/room/{room_id} → Server
↓
Server loads config + in-memory session from rooms.json / sessions dict
↓
Server → 200 OK + { room_id, room: { config, session } }
↓
Client renders the game screen and opens a WebSocket to /ws/{room_id}/{user_email}
↓
Server adds user to session, sends "room_state" to the joining client
↓
Server broadcasts "user_joined" (full users list) to everyone else
↓
Client applies room_state and re-renders
```

### Bingo Selection
```
User clicks bingo cell
↓
Client toggles the cell locally and sends "bingo_select" { row, col }
↓
Server toggles the cell in session.bingo_selections
↓
Server broadcasts "bingo_updated" (full bingo_selections map) to all clients in room
↓
All clients re-render the grid, applying the visibility rules
```

### Poker Selection
```
User clicks a poker value
↓
Client sends "poker_select" { value }
↓
Server validates the value and overwrites session.poker_selections[email]
↓
Server broadcasts "poker_updated" { email, has_selection: true }
↓
All clients re-render the participant list ("ready" instead of "waiting")
```

### Reveal Round
```
User clicks "Reveal All"
↓
Client → WebSocket "reveal" message
↓
Server sets session.revealed = true
↓
Server broadcasts "revealed" with bingo_selections + poker_selections
↓
All clients render:
  - Bingo grid with every participant's color dots, cells frozen
  - Each participant's poker value in the participant list
  - Average of numeric votes plus a count of "split" votes
  - Reveal button disabled, Reset button enabled
```

## Room State Management

### Normal Flow (Before Reveal)
```
Reveal Button: ENABLED
Reset Button: DISABLED
Poker values: Hidden (others see "ready" / "waiting")
Bingo: User can toggle cells; worker selections visible only to themselves
```

### After Reveal
```
Reveal Button: DISABLED
Reset Button: ENABLED
Poker values: Visible per participant, plus average and split count
Bingo: Grid frozen, all selections visible with owner colors
```

### After Reset
```
Returns to "Normal Flow"
All bingo selections cleared
All poker selections cleared
revealed flag = false
Users remain in room
```

## Error Handling

### Connection Loss
- No automatic reconnection is implemented; when the WebSocket closes the client simply clears `appState.ws`
- The user must re-enter the room (or reload the page) to reconnect
- The server does not buffer or queue messages during a disconnection

### Color Palette Wraparound (10 colors)
- There is no hard user limit; if more than 10 users join a room, colors wrap around and repeat (`get_color_by_index` uses modulo)

### Invalid or Unknown IDs
- `GET /api/room/{room_id}` returns `400` for a malformed room ID and `404` when the room does not exist
- The WebSocket endpoint returns `401` for an unknown user and `404` for an unknown room

### Malformed Messages
- Server validates JSON structure and message `type`
- Unknown `type` or invalid JSON returns an `error` message to the sender
- Other invalid payloads (missing `row`/`col`, empty or invalid poker value) are silently ignored

## Performance Considerations

- In-memory session state for active rooms; room configs are loaded once at startup
- Broadcasts are scoped to the connections of a single room, not all connections
- Bingo grid fixed at 25 cells; poker values fixed at 9 options
- Dead sockets are pruned during each broadcast
- Session state is cleaned up when the last user leaves a room

---

*Last Updated: 2026-08-18*
