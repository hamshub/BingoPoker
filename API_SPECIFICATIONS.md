# API Specifications - BingoPoker

## Overview

BingoPoker uses a hybrid REST + WebSocket API architecture. REST endpoints handle initial operations (user registration, room creation, loading), while WebSocket provides real-time bidirectional communication for gameplay.

---

## HTTP Endpoints

### Base URL
```
http://localhost:8081
```

---

### 1. Serve HTML
**Endpoint**: `GET /`

**Description**: Serves the main application HTML

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

---

### 2. Health Check
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
  "service": "BingoPoker API"
}
```

---

### 3. Register User
**Endpoint**: `POST /api/user`

**Description**: Register a new user or get existing user profile

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

`role` defaults to `"worker"` if omitted. Valid values: `"worker"` (developer/tester) or `"observer"` (PO/stakeholder).

**Response (New User)**:
```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "user": {
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
    "email": "alice@company.com",
    "username": "Alice Johnson",
    "role": "worker"
  },
  "is_new": false
}
```

**Error Responses**:

Invalid email format:
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_email",
  "message": "Please provide a valid email address"
}
```

Invalid username:
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_username",
  "message": "Username must be 1-50 characters"
}
```

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
  "message": "User profile does not exist"
}
```

---

### 5. Update User Profile
**Endpoint**: `PUT /api/user/{email}`

**Description**: Update user profile (username only)

**Request**:
```http
PUT /api/user/alice@company.com HTTP/1.1
Host: localhost:8081
Content-Type: application/json

{
  "username": "Alice Smith"
}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "user": {
    "email": "alice@company.com",
    "username": "Alice Smith",
    "role": "worker"
  }
}
```

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
  "message": "Room name must be 1-100 characters"
}
```

Invalid grid (not 5x5):
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_grid",
  "message": "Grid must be exactly 5x5"
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

**Description**: Get room configuration and current state

**Request**:
```http
GET /api/room/room-abc123xy HTTP/1.1
Host: localhost:8081
```

**Response (Not Revealed)**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "room_id": "room-abc123xy",
  "room": {
    "config": {
      "room_id": "room-abc123xy",
      "name": "Sprint 42 Planning",
      "config": { "grid": [...] },
      "created_at": "2026-08-12T10:30:00Z",
      "created_by": "alice@company.com"
    },
    "session": {
      "users": [
        { "email": "alice@company.com", "username": "Alice Johnson", "role": "worker", "color": "#E63946" }
      ],
      "bingo_selections": {
        "alice@company.com": [[0, 0], [1, 2]]
      },
      "poker_selections": {
        "alice@company.com": "8"
      },
      "revealed": false
    }
  }
}
```

**Response (Revealed)**: identical shape, with `session.revealed: true` and all `poker_selections` values populated.

**Error Response**:
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error": "room_not_found",
  "message": "Room does not exist"
}
```

---

### 8. List Active Rooms
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
      "created_at": "2026-08-12T10:30:00Z",
      "created_by": "alice@company.com"
    },
    {
      "room_id": "room-def456ab",
      "name": "Design Sprint 2026",
      "user_count": 1,
      "created_at": "2026-08-11T14:30:00Z",
      "created_by": "bob@company.com"
    }
  ]
}
```

---

## WebSocket Endpoints

### Connection
**URL**: `ws://localhost:8081/ws/{room_id}/{user_email}`

The room and user email are path parameters — there is no separate "join" message; connecting to this URL joins the room immediately (the server validates the user and room exist first, returning 401/404 otherwise).

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

**Valid Values**: `"0"`, `"1"`, `"2"`, `"3"`, `"5"`, `"8"`, `"13"`, `"21"`, `"split"`

**Server Processing**:
- Overwrites any previous selection for this user
- Broadcasts `poker_updated` (without the value) to all clients in the room

---

#### 3. Reveal Votes
**Message Type**: `reveal`

**Structure**:
```json
{ "type": "reveal", "payload": {} }
```

**Server Processing**:
- Sets the session's `revealed` flag to `true`
- Broadcasts `revealed` with the full `bingo_selections` and `poker_selections` to all clients

---

#### 4. Reset Round
**Message Type**: `reset`

**Structure**:
```json
{ "type": "reset", "payload": {} }
```

**Server Processing**:
- Clears `bingo_selections` and `poker_selections`, sets `revealed` back to `false`
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
      "config": { "grid": [...] },
      "created_at": "2026-08-12T10:30:00Z",
      "created_by": "alice@company.com"
    },
    "session": {
      "users": [
        { "email": "alice@company.com", "username": "Alice Johnson", "role": "worker", "color": "#E63946" }
      ],
      "bingo_selections": { "alice@company.com": [[0, 0], [1, 3]] },
      "poker_selections": { "alice@company.com": "8" },
      "revealed": false
    }
  }
}
```

---

#### 2. User Joined
**Message Type**: `user_joined`

**Purpose**: Sent to everyone else in the room (sender excluded) when a new client connects

**Structure**:
```json
{
  "type": "user_joined",
  "payload": {
    "users": [
      { "email": "alice@company.com", "username": "Alice Johnson", "role": "worker", "color": "#E63946" },
      { "email": "bob@company.com", "username": "Bob Smith", "role": "worker", "color": "#F4A300" }
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
    "users": [ /* remaining users, full list */ ]
  }
}
```

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

**Note**: The actual poker value is not sent until `reveal`. Clients re-render the participants list to show "ready"/"waiting" state.

---

#### 6. Revealed
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

---

#### 7. Round Reset
**Message Type**: `round_reset`

**Structure**:
```json
{ "type": "round_reset", "payload": {} }
```

---

#### 8. Replaced (duplicate connection)
**Message Type**: `replaced`

**Purpose**: Sent to an existing connection when the same user opens a new tab/window and joins the same room; the server then closes this connection

**Structure**:
```json
{ "type": "replaced", "payload": {} }
```

---

#### 9. Error
**Message Type**: `error`

**Structure**:
```json
{
  "type": "error",
  "payload": { "message": "Unknown type: some_bad_type" }
}
```

Sent only for malformed JSON or an unrecognized `type` field — there is no granular error-code system for validation failures (e.g. invalid cell, invalid poker value); the server just silently ignores those requests.

---

## Error Handling

### REST Error Response Format
```json
{
  "error": "error_code",
  "message": "Human-readable message"
}
```

### Common REST Error Codes
- `invalid_input` — missing required field
- `invalid_email` — email format invalid
- `invalid_room_name` — room name invalid
- `invalid_grid` — grid not 5×5
- `invalid_room_id` — room ID doesn't match `room-{8 alphanumeric}` format
- `duplicate_name` — a room with that name already exists
- `room_not_found` — room doesn't exist
- `user_not_found` — user doesn't exist
- `registration_failed` / `creation_failed` — validation failed inside the manager
- `invalid_json` — malformed JSON body
- `server_error` — unhandled exception (500)

There is currently no rate limiting implemented.

---

## WebSocket Reconnection

There is no automatic client-side reconnection logic. If the WebSocket closes (network drop, server restart, or a `replaced` event from another tab), the client sets `appState.ws = null` and the user must rejoin the room manually (navigating back triggers `joinRoom()` again, which reconnects).

---

*Last Updated: 2026-08-13*
