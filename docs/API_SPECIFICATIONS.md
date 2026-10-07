# API Specifications - BingoPoker

## Overview

BingoPoker uses a hybrid REST + WebSocket API architecture. REST endpoints handle initial operations (user registration, room creation, listing, deletion), while WebSocket provides real-time bidirectional communication for gameplay.

All REST responses are JSON. Errors always use the shape `{ "error": "<code>", "message": "<text>" }`.

---

## HTTP Endpoints

### Base URL
```
http://localhost:8081
```

Host and port come from the `HOST` (default `0.0.0.0`) and `PORT` (default `8081`) environment variables.

---

### 1. Serve HTML
**Endpoint**: `GET /`

**Description**: Serves `frontend/index.html`

**Request**:
```http
GET / HTTP/1.1
Host: localhost:8081
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: text/html

<!doctype html>
<html>...</html>
```

Static assets are mounted at `/css`, `/imgs`, `/js`, and `/templates`, served from the matching `frontend/` subdirectories.

---

### 2. Health Check and Version
**Endpoint**: `GET /health`

**Description**: Server health status check

**Request**:
```http
GET /health HTTP/1.1
Host: localhost:8081
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "ok",
  "service": "BingoPoker API",
  "version": "dev"
}
```

**Endpoint**: `GET /api/version`

**Description**: Reports the running build. Values come from the `APP_VERSION` (default `"dev"`) and `BUILD_DATE` (default `""`) environment variables, which CI sets at image build time to the commit SHA and a UTC ISO timestamp. The frontend shows `Version <first 7 chars> · <YYYY-MM-DD>` (or `Development build`) on the room list screen.

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "version": "<commit-sha>",
  "build_date": "2026-10-07T12:00:00Z"
}
```

---

### 3. Register User
**Endpoint**: `POST /api/user`

**Description**: Register a new user or get an existing user's profile

**Request**:
```http
POST /api/user HTTP/1.1
Host: localhost:8081
Content-Type: application/json

{
  "email": "alice@company.com",
  "username": "Alice Johnson",
  "role": "worker"
}
```

`role` defaults to `"worker"` if omitted. Valid values: `"worker"` (developer/tester) or `"observer"` (PO/stakeholder); any other value falls back to `"worker"`.

**Response (New User)**:
```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "user": {
    "user_id": "9f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f",
    "email": "alice@company.com",
    "username": "Alice Johnson",
    "role": "worker"
  },
  "is_new": true
}
```

**Response (Existing User)**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "user": {
    "user_id": "9f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f",
    "email": "alice@company.com",
    "username": "Alice Johnson",
    "role": "worker"
  },
  "is_new": false
}
```

**Note**: `email` in the response is echoed back from the request. Plain emails are never persisted — the server stores only an HMAC-SHA256 digest (see DATA_STRUCTURES.md).

**Error Responses**:

Missing email or username:
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_input",
  "message": "Email and username required"
}
```

Validation failure inside the user manager (bad email format, username length):
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "registration_failed",
  "message": "Email format is invalid"
}
```

A malformed JSON body returns `400 invalid_json`; an unhandled exception returns `500 server_error`.

---

### 4. Get User Profile
**Endpoint**: `GET /api/user/{email}`

**Description**: Get user profile by email

**Request**:
```http
GET /api/user/alice@company.com HTTP/1.1
Host: localhost:8081
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "user": {
    "user_id": "9f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f",
    "email": "alice@company.com",
    "username": "Alice Johnson",
    "role": "worker"
  }
}
```

**Error Response**:
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error": "user_not_found",
  "message": "User alice@company.com not found"
}
```

---

### 5. Update User Profile
**Endpoint**: `PUT /api/user/{email}`

**Description**: Update the user's username and/or role. At least one of the two fields must be present.

**Request**:
```http
PUT /api/user/alice@company.com HTTP/1.1
Host: localhost:8081
Content-Type: application/json

{
  "username": "Alice Smith",
  "role": "observer"
}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "user": {
    "user_id": "9f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f",
    "email": "alice@company.com",
    "username": "Alice Smith",
    "role": "observer"
  }
}
```

**Error Responses**:
- `400 invalid_input` — neither `username` nor `role` provided
- `400 update_failed` — username length invalid, or role is not `worker`/`observer`
- `400 invalid_json` — malformed JSON body
- `404 user_not_found` — no such user

---

### 6. Create Room
**Endpoint**: `POST /api/room`

**Description**: Create a new bingo poker room

**Request**:
```http
POST /api/room HTTP/1.1
Host: localhost:8081
Content-Type: application/json

{
  "name": "Sprint 42 Planning",
  "created_by": "alice@company.com",
  "grid": [
    ["Story A", "Story B", "Story C", "Story D", "Story E"],
    ["Story F", "Story G", "Story H", "Story I", "Story J"],
    ["Story K", "Story L", "Story M", "Story N", "Story O"],
    ["Story P", "Story Q", "Story R", "Story S", "Story T"],
    ["Story U", "Story V", "Story W", "Story X", "Story Y"]
  ]
}
```

`created_by` is the creator's **email**. The server resolves it to the creator's random user ID and stores only that ID.

**Response**:
```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "room_id": "room-abc123xy",
  "message": "Room created successfully"
}
```

Clients build the shareable invite link client-side from `location.origin` + `?r={room_id}` — the server does not return a `join_url`.

**Error Responses**:

Invalid room name:
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_room_name",
  "message": "Room name must be 100 characters or less"
}
```

Invalid grid (not a 5x5 array of strings):
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_grid",
  "message": "Grid must be 5x5 array of strings"
}
```

Missing `created_by`:
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_input",
  "message": "created_by (email) required"
}
```

Creator is not a registered user:
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error": "user_not_found",
  "message": "Creator is not a registered user"
}
```

Duplicate room name:
```http
HTTP/1.1 409 Conflict
Content-Type: application/json

{
  "error": "duplicate_name",
  "message": "A room named 'Sprint 42 Planning' already exists"
}
```

---

### 7. Get Room Configuration
**Endpoint**: `GET /api/room/{room_id}`

**Description**: Get room configuration and current session state

**Request**:
```http
GET /api/room/room-abc123xy HTTP/1.1
Host: localhost:8081
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "room_id": "room-abc123xy",
  "room": {
    "config": {
      "room_id": "room-abc123xy",
      "name": "Sprint 42 Planning",
      "config": { "grid": [] },
      "created_at": "2026-08-12T10:30:00.123456",
      "created_by": "9f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f"
    },
    "session": {
      "users": [
        {
          "user_id": "9f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f",
          "email": "alice@company.com",
          "username": "Alice Johnson",
          "role": "worker",
          "color": "#E63946"
        }
      ],
      "bingo_selections": {
        "alice@company.com": [[0, 0], [1, 2]]
      },
      "poker_selections": {
        "alice@company.com": "8"
      },
      "ready": ["alice@company.com"],
      "auto_reveal": false,
      "revealed": false,
      "color_counter": 1
    }
  }
}
```

`config.created_by` is a **user ID**, never an email. It may be `null` for legacy rooms whose creator could not be resolved during migration.

If nobody is currently connected, `session` is the empty default (`users: []`, empty selection maps, `ready: []`, `auto_reveal: false`, `revealed: false`).

**Error Responses**:
- `400 invalid_room_id` — the ID does not match `room-{8 alphanumeric}`
- `404 room_not_found` — no such room

---

### 8. List Rooms
**Endpoint**: `GET /api/rooms`

**Description**: Get list of all persisted rooms with live participant counts

**Request**:
```http
GET /api/rooms HTTP/1.1
Host: localhost:8081
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "rooms": [
    {
      "room_id": "room-abc123xy",
      "name": "Sprint 42 Planning",
      "user_count": 2,
      "created_at": "2026-08-12T10:30:00.123456",
      "created_by": "9f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f"
    },
    {
      "room_id": "room-def456ab",
      "name": "Design Sprint 2026",
      "user_count": 0,
      "created_at": "2026-08-11T14:30:00.654321",
      "created_by": null
    }
  ],
  "count": 2
}
```

`created_by` is a user ID (or `null`), never an email. The frontend compares it against the logged-in user's `user_id` to decide whether to show the delete action.

---

### 9. Delete Room
**Endpoint**: `DELETE /api/room/{room_id}`

**Description**: Delete a room and its session state. Only the room creator may do this.

**Request**:
```http
DELETE /api/room/room-abc123xy HTTP/1.1
Host: localhost:8081
Content-Type: application/json

{
  "created_by": "alice@company.com"
}
```

`created_by` is the requester's **email**; the server resolves it to a user ID and compares it with the room's stored creator ID.

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "message": "Room deleted successfully"
}
```

**Error Responses**:
- `400 invalid_room_id` — malformed room ID
- `400 invalid_input` — missing `created_by`
- `400 invalid_json` — malformed JSON body
- `403 unauthorized` — requester is not the room creator
- `404 room_not_found` — no such room

---

### 10. Debug Endpoints (DEBUG mode only)

Registered only when the `DEBUG` environment variable is `true`. **They wipe all persisted data.**

| Endpoint | Effect | Response |
| --- | --- | --- |
| `DELETE /api/debug/users` | Clears `users.json` and the in-memory user registry | `{"message": "All users deleted"}` |
| `DELETE /api/debug/rooms` | Clears `rooms.json` and all in-memory sessions | `{"message": "All rooms deleted"}` |

---

### 11. Admin Pages (ADMIN_PASSWORD only)

Server-rendered HTML pages, registered only when the `ADMIN_PASSWORD` environment variable is non-empty. Without it a warning is logged at startup and both paths return `404`.

| Endpoint | Content |
| --- | --- |
| `GET /logs` | List of the current and rotated log files (newest first) and the selected file's content. `?file=<name>` selects a file; only names from the listing are accepted (`404 Log file not found` otherwise, which prevents path traversal). Files over 2 MB show their last 2 MB. |
| `GET /analytics` | Usage statistics: total cards (registered users, rooms, days with activity, rooms created, room joins, rounds revealed, auto-reveals, votes cast, average participants per round, most popular card, ☕ share of votes), a vote distribution bar chart, and a table of the last 30 active days. No external JS/CSS libraries. |

**Authentication**: HTTP Basic auth. Any username is accepted; the password must equal `ADMIN_PASSWORD` (constant-time comparison).
- Missing or wrong credentials → `401 Authentication required` with `WWW-Authenticate: Basic realm="BingoPoker admin"`
- A wrong password is logged as a warning and the response is delayed by 1 s
- Successful responses carry `Cache-Control: no-store`

Basic auth sends the password with every request, so these pages must only be reached over HTTPS (Caddy in production).

---

## WebSocket Endpoints

### Connection
**URL**: `ws://localhost:8081/ws/{room_id}/{user_email}`

The room and user email are path parameters — there is no separate "join" message; connecting to this URL joins the room immediately.

Before upgrading, the server validates:
- the user is registered — otherwise `HTTP 401 User not found`
- the room exists — otherwise `HTTP 404 Room not found`

**Upgrade Request**:
```http
GET /ws/room-abc123xy/alice%40company.com HTTP/1.1
Host: localhost:8081
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: ...
Sec-WebSocket-Version: 13
```

**Response**:
```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: ...
```

**Duplicate connections**: if the same email is already connected to that room, the previous socket receives `{"type": "replaced", "payload": {}}` and is closed before the new one is registered.

---

## WebSocket Messages

All messages (both directions) use the envelope `{ "type": "...", "payload": {...} }`. There is no `room_id`, `user_email`, or `timestamp` field on individual messages — the room and user are bound to the connection itself (from the `/ws/{room_id}/{user_email}` URL), and the server does not timestamp messages.

### Client → Server Messages

#### 1. Select Bingo Cell
**Message Type**: `bingo_select`

**Purpose**: Toggle a bingo card cell selection on/off for the connected user

**Structure**:
```json
{
  "type": "bingo_select",
  "payload": { "row": 1, "col": 3 }
}
```

**Server Processing**:
- Ignored silently if `row` or `col` is missing, or if the coordinates fall outside 0–4
- Toggles the cell in the session's `bingo_selections` for this user (add if absent, remove if present)
- No validation against `revealed` state — selections can technically still be sent after reveal, but the UI disables clicking
- Broadcasts `bingo_updated` to all clients in the room (including sender)

---

#### 2. Select Poker Value
**Message Type**: `poker_select`

**Purpose**: Record the user's story point estimate (hidden until reveal)

**Structure**:
```json
{
  "type": "poker_select",
  "payload": { "value": "8" }
}
```

**Valid Values**: `"coffee"`, `"0"`, `"1"`, `"2"`, `"3"`, `"5"`, `"8"`, `"13"`, `"21"`, `"split"`

`"coffee"` (shown as ☕) is every user's default estimate and is excluded from the post-reveal average. Choosing it explicitly is stored and counts as a vote like any other value.

**Server Processing**:
- Overwrites any previous selection for this user
- Missing values, or values outside the allowed list, are ignored silently
- Broadcasts `poker_updated` (without the value) to all clients in the room

---

#### 3. Toggle Ready
**Message Type**: `ready_toggle`

**Purpose**: Flip the user's ready flag for the current round (shown as a green tick next to their name)

**Structure**:
```json
{ "type": "ready_toggle", "payload": {} }
```

**Server Processing**:
- Adds the user's email to `session.ready`, or removes it if already present
- Broadcasts `ready_updated` with the full `ready` list to all clients in the room
- The UI disables the Ready button after reveal; the server does not check `revealed`
- If auto-reveal is on and every participant is ready, the server reveals the round right away (see `auto_reveal_set`)

---

#### 4. Set Auto-reveal
**Message Type**: `auto_reveal_set`

**Purpose**: Turn the room's auto-reveal setting on or off. It is shared by everyone in the room.

**Structure**:
```json
{ "type": "auto_reveal_set", "payload": { "enabled": true } }
```

**Server Processing**:
- Stores `enabled` in `session.auto_reveal`; a non-boolean value is ignored silently
- Broadcasts `auto_reveal_updated` to all clients in the room
- While it is on, the server reveals the round (broadcasting `revealed`, exactly as for `reveal`) as soon as every participant in the session is ready. This is checked after `ready_toggle`, after `auto_reveal_set`, and when a participant leaves
- The setting survives `reset`; it lasts as long as the in-memory session (until the last participant leaves)

---

#### 5. Reveal Votes
**Message Type**: `reveal`

**Structure**:
```json
{ "type": "reveal", "payload": {} }
```

**Server Processing**:
- Sets the session's `revealed` flag to `true`
- Broadcasts `revealed` with the full `bingo_selections` and `poker_selections` to all clients

---

#### 6. Reset Round
**Message Type**: `reset`

**Structure**:
```json
{ "type": "reset", "payload": {} }
```

**Server Processing**:
- Clears `bingo_selections`, `poker_selections` and `ready`, sets `revealed` back to `false`
- Broadcasts `round_reset` (empty payload) to all clients

---

### Server → Client Messages (Broadcasts)

#### 1. Room State Sync
**Message Type**: `room_state`

**Purpose**: Sent once to a client immediately after it connects

**Structure**:
```json
{
  "type": "room_state",
  "payload": {
    "config": {
      "room_id": "room-abc123xy",
      "name": "Sprint 42 Planning",
      "config": { "grid": [] },
      "created_at": "2026-08-12T10:30:00.123456",
      "created_by": "9f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f"
    },
    "session": {
      "users": [
        {
          "user_id": "9f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f",
          "email": "alice@company.com",
          "username": "Alice Johnson",
          "role": "worker",
          "color": "#E63946"
        }
      ],
      "bingo_selections": { "alice@company.com": [[0, 0], [1, 3]] },
      "poker_selections": { "alice@company.com": "8" },
      "ready": ["alice@company.com"],
      "auto_reveal": false,
      "revealed": false,
      "color_counter": 1
    }
  }
}
```

---

#### 2. User Joined
**Message Type**: `user_joined`

**Purpose**: Sent to everyone else in the room (the joining client excluded) when a new client connects

**Structure**:
```json
{
  "type": "user_joined",
  "payload": {
    "users": [
      { "user_id": "9f1c...", "email": "alice@company.com", "username": "Alice Johnson", "role": "worker", "color": "#E63946" },
      { "user_id": "7b2a...", "email": "bob@company.com", "username": "Bob Smith", "role": "worker", "color": "#F4A300" }
    ]
  }
}
```

`payload.users` is always the **full current users list**, not just the joining user.

---

#### 3. User Left
**Message Type**: `user_left`

**Structure**:
```json
{
  "type": "user_left",
  "payload": {
    "email": "alice@company.com",
    "users": []
  }
}
```

`payload.users` is the remaining users (full list).

---

#### 4. Bingo Selection Updated
**Message Type**: `bingo_updated`

**Structure**:
```json
{
  "type": "bingo_updated",
  "payload": {
    "bingo_selections": {
      "alice@company.com": [[0, 0], [1, 3]],
      "bob@company.com": [[2, 4]]
    }
  }
}
```

`payload.bingo_selections` is the full map for all users, not a single delta — cell coordinates are `[row, col]` pairs.

Visibility is enforced client-side: a **worker**'s cells are rendered only for that worker until reveal, while an **observer**'s cells are always shown to everyone.

---

#### 5. Poker Selection Updated
**Message Type**: `poker_updated`

**Structure**:
```json
{
  "type": "poker_updated",
  "payload": { "email": "alice@company.com", "has_selection": true }
}
```

**Note**: The actual poker value is not sent until `reveal`. Clients re-render the participants list to show "voted"/"waiting" state.

---

#### 6. Ready Updated
**Message Type**: `ready_updated`

**Structure**:
```json
{
  "type": "ready_updated",
  "payload": { "ready": ["alice@company.com", "bob@company.com"] }
}
```

**Note**: Carries the full list of ready users. Clients show a green ✓ next to each of them in the participants list and toggle the state of their own Ready button.

---

#### 7. Auto-reveal Updated
**Message Type**: `auto_reveal_updated`

**Structure**:
```json
{ "type": "auto_reveal_updated", "payload": { "enabled": true } }
```

**Note**: Clients update the "Auto-reveal when everyone is ready" checkbox under Round Controls.

---

#### 8. Revealed
**Message Type**: `revealed`

**Structure**:
```json
{
  "type": "revealed",
  "payload": {
    "bingo_selections": {
      "alice@company.com": [[0, 0], [1, 3]],
      "bob@company.com": [[2, 4]]
    },
    "poker_selections": {
      "alice@company.com": "8",
      "bob@company.com": "13"
    }
  }
}
```

Users without an entry in `poker_selections` never voted and kept the default ☕; clients display ☕ for them. All ☕ values, explicit or default, are left out of the average.

---

#### 9. Round Reset
**Message Type**: `round_reset`

**Structure**:
```json
{ "type": "round_reset", "payload": {} }
```

---

#### 10. Replaced (duplicate connection)
**Message Type**: `replaced`

**Purpose**: Sent to an existing connection when the same user opens a new tab/window and joins the same room; the server then closes this connection

**Structure**:
```json
{ "type": "replaced", "payload": {} }
```

---

#### 11. Error
**Message Type**: `error`

**Structure**:
```json
{
  "type": "error",
  "payload": { "message": "Unknown type: some_bad_type" }
}
```

Sent only for malformed JSON (message `"Invalid JSON"`) or an unrecognized `type` field — there is no granular error-code system for validation failures (e.g. invalid cell, invalid poker value); the server just silently ignores those requests.

---

## Validation Rules

Backend validation lives in `backend/utils/validators.py`:

| Field | Rule |
| --- | --- |
| Email | `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$` |
| Username | 1–50 characters |
| Room name | 1–100 characters |
| Room ID | `^room-[a-zA-Z0-9]{8}$` |
| Grid | List of 5 lists of 5 strings |
| Poker value | One of `coffee`, `0`, `1`, `2`, `3`, `5`, `8`, `13`, `21`, `split` |
| Bingo cell | Row and column each in 0–4 (checked in `RoomManager`) |

There is no per-cell text length validator on the backend; the 50-character cap on grid cells is only a frontend `maxLength` on the editor inputs.

---

## Error Handling

### REST Error Response Format
```json
{
  "error": "error_code",
  "message": "Human-readable message"
}
```

### REST Error Codes
- `invalid_input` — missing required field
- `invalid_room_name` — room name invalid
- `invalid_grid` — grid is not a 5×5 array of strings
- `invalid_room_id` — room ID doesn't match `room-{8 alphanumeric}` format
- `duplicate_name` — a room with that name already exists
- `room_not_found` — room doesn't exist
- `user_not_found` — user doesn't exist / creator not registered
- `unauthorized` — requester is not the room creator
- `registration_failed` / `update_failed` / `creation_failed` / `deletion_failed` — validation failed inside the manager
- `invalid_json` — malformed JSON body
- `server_error` — unhandled exception (500)

There is currently no rate limiting implemented (apart from the 1 s delay after a failed admin login).

---

## Logging

Server events are written to `<LOG_DIR>/bingopoker.log` (INFO and above to file, WARNING and above to console). `LOG_DIR` defaults to `backend/logs`; the Docker image sets it to `/app/data/logs` so logs live in the data volume. The file rotates at midnight to `bingopoker.log.YYYY-MM-DD` and 30 files are kept (days without log lines produce no file). Logs can be browsed on the [`/logs` admin page](#11-admin-pages-admin_password-only). Logged events: user registered, user login, room created, room deleted, user joined room, user left room. Log lines reference `user_id`, never the email address. The `aiohttp.access` and `asyncio` loggers are raised to WARNING to suppress noise and to keep emails out of access-log URLs.

---

## WebSocket Reconnection

There is no automatic client-side reconnection logic. If the WebSocket closes (network drop, server restart, or a `replaced` event from another tab), the client sets `appState.ws = null` and the user must rejoin the room manually (navigating back triggers `joinRoom()` again, which reconnects).

---

*Last Updated: 2026-10-07*
