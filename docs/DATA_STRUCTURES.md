# Data Structures - BingoPoker

## Overview

BingoPoker uses two primary JSON files for persistence and several in-memory structures for active room state. Plain email addresses are never written to disk.

---

## File-Based Storage

### 1. `backend/data/users.json`

Persistent user registry, keyed by a random user ID. Emails are stored only as a non-reversible HMAC digest; no color or timestamps are stored.

**Location**: `backend/data/users.json` (directory configurable via the `DATA_DIR` environment variable)

**Schema**:
```json
{
  "[user_id]": {
    "user_id": "string (uuid4 hex, 32 chars)",
    "email_hash": "string (HMAC-SHA256 hex digest)",
    "username": "string",
    "role": "worker | observer"
  }
}
```

**Example**:
```json
{
  "9f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f": {
    "user_id": "9f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f",
    "email_hash": "3b1f...c9a2",
    "username": "Alice Johnson",
    "role": "observer"
  },
  "7b2a1c0d9e8f7a6b5c4d3e2f1a0b9c8d": {
    "user_id": "7b2a1c0d9e8f7a6b5c4d3e2f1a0b9c8d",
    "email_hash": "a77e...41bd",
    "username": "Bob Smith",
    "role": "worker"
  }
}
```

**Email Hashing**:
- `email_hash = HMAC-SHA256(pepper, email.strip().lower())`, hex encoded
- The pepper comes from the `EMAIL_HASH_PEPPER` environment variable; if unset, a random pepper is generated once and stored in `backend/data/.email_pepper`
- Lookups work by hashing the incoming email and consulting an in-memory `email_hash -> user_id` index
- Because hashing is one-way, an email can never be recovered from storage

**Legacy Migration**:
- On `UserManager.load()`, any record that is email-keyed or lacks `email_hash` is converted to the hashed/UID format and the file is rewritten

**Operations**:
- **Read**: Load all users on startup
- **Write**: When a new user registers
- **Update**: When a user updates their username or role
- **Delete**: Only via the DEBUG-mode `DELETE /api/debug/users` endpoint (wipes everything)

**Constraints**:
- `user_id` is the primary key and is immutable
- Username and role can be updated at any time
- Role is `worker` (developer/tester) or `observer` (PO/stakeholder)
- Color is **not stored** — assigned per room session at join time

---

### 2. `backend/data/rooms.json`

Persistent room configurations. Stores the bingo card setup and room metadata.

**Location**: `backend/data/rooms.json`

**Schema**:
```json
{
  "[room_id]": {
    "room_id": "string",
    "name": "string",
    "config": {
      "grid": [
        ["string", "string", "string", "string", "string"],
        ["string", "string", "string", "string", "string"],
        ["string", "string", "string", "string", "string"],
        ["string", "string", "string", "string", "string"],
        ["string", "string", "string", "string", "string"]
      ]
    },
    "created_at": "string (ISO 8601, UTC, no timezone suffix)",
    "created_by": "string (user_id) | null"
  }
}
```

**Example**:
```json
{
  "room-abc123xy": {
    "room_id": "room-abc123xy",
    "name": "Sprint 42 Planning",
    "created_at": "2026-08-12T10:00:00.123456",
    "created_by": "9f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f",
    "config": {
      "grid": [
        ["User Login", "API Endpoint", "Database", "Frontend", "Auth"],
        ["Dashboard", "Reports", "Notifications", "Search", "Admin Panel"],
        ["Payments", "Settings", "¯\\_(\u30c4)_/¯", "Profile", "Help"],
        ["Onboarding", "Export", "Import", "Analytics", "Security"],
        ["Mobile App", "Cache", "Queue", "Logging", "Monitoring"]
      ]
    }
  },
  "room-def456ab": {
    "room_id": "room-def456ab",
    "name": "Design Sprint 2026",
    "created_at": "2026-08-11T14:30:00.654321",
    "created_by": null,
    "config": {
      "grid": [
        ["Wireframes", "Design System", "Icons", "Typography", "Colors"],
        ["Buttons", "Forms", "Cards", "Modals", "Navigation"],
        ["Layout", "Responsive", "¯\\_(\u30c4)_/¯", "Accessibility", "Animations"],
        ["Micro-interactions", "Feedback", "Loading", "Errors", "Success"],
        ["Mobile Design", "Tablet View", "Desktop View", "Dark Mode", "Themes"]
      ]
    }
  }
}
```

**Room ID Format**:
- Generated as `room-{8 random alphanumeric characters}` using `secrets.choice`
- Example: `room-abc123xy`
- Matches the validator pattern `^room-[a-zA-Z0-9]{8}$` and is URL-safe

**Creator Ownership**:
- `created_by` holds the creator's random **user ID**, never an email
- `RoomManager.migrate_creator_ids()` runs at startup and rewrites legacy plain-email values to user IDs
- If the legacy creator is no longer registered, `created_by` becomes `null` and the room is orphaned (nobody can delete it through the API)

**Special Grid Cell**:
- Center cell (2,2) is styled differently in the UI but otherwise behaves identically to all other cells
- The center cell text is defined in the grid config like any other cell

**Operations**:
- **Read**: On startup, room join, or page load
- **Write**: When a room is created
- **Delete**: `DELETE /api/room/{room_id}` by the creator, or the DEBUG-mode `DELETE /api/debug/rooms` endpoint

**Constraints**:
- 5x5 grid is fixed; every cell must be a string
- Room name is 1–100 characters and must be unique among existing rooms
- Room ID is immutable

---

## In-Memory Structures (Runtime)

### 3. Room Session State

Active room state stored in server memory under `RoomManager.sessions[room_id]`. Never persisted; the entry is deleted as soon as the last user leaves.

**Structure**:
```python
{
  "users": [
    {
      "user_id": "string",
      "email": "string",
      "username": "string",
      "role": "worker | observer",
      "color": "string (hex, assigned at join time in rolling order)"
    },
  ],
  "bingo_selections": {
    "[user_email]": [(row, col), ...]  # tuples in memory, serialized as [row, col] lists
  },
  "poker_selections": {
    "[user_email]": "8"  # One of: "0", "1", "2", "3", "5", "8", "13", "21", "split"
  },
  "revealed": False,
  "color_counter": 2  # Monotonic counter for color assignment; never decreases
}
```

The entries in `users` are the public user profile (`user_id`, `email`, `username`, `role`) plus the session-assigned `color`. Session maps are keyed by email, because the WebSocket connection is identified by email.
    },
    "revealed": false,
    "color_counter": 2  # Monotonic counter for color assignment; never decreases
  }
}
```

**Example Bingo Selections**:
```json
{
  "alice@company.com": [[0, 0], [0, 1], [1, 2]],
  "bob@company.com": [[0, 0], [2, 2], [4, 4]],
  "carol@company.com": [[1, 1], [2, 2], [3, 3]]
}
```

**Cell Coordinates**: Row and column indices 0–4. Coordinates outside that range are rejected.
Cell [2][2] is the center cell — styled differently, but with no special game behavior.

**Selection Semantics**:
- `bingo_select` toggles a cell: it is added if absent and removed if present
- `poker_select` overwrites the user's previous value
- A worker's bingo cells are visible only to that worker until reveal; an observer's cells are always visible to everyone
- Poker values stay hidden (only `has_selection` is broadcast) until reveal
- Leaving the room removes the user's entries from both selection maps

**Poker Values**:
- `"0"` - Zero/Not started
- `"1"` - One
- `"2"` - Two
- `"3"` - Three
- `"5"` - Five
- `"8"` - Eight
- `"13"` - Thirteen
- `"21"` - Twenty-one
- `"split"` - Cannot estimate/too big

---

## Color Palette

### 4. Predefined Color List

10 colors for user identification, assigned in rolling order (`backend/utils/color_palette.py`).

**List**:
```
1.  #E63946 - Red
2.  #F4A300 - Amber
3.  #2EC4B6 - Teal
4.  #A8DADC - Ice Blue
5.  #8338EC - Violet
6.  #06D6A0 - Mint Green
7.  #FF6B35 - Orange
8.  #3A86FF - Royal Blue
9.  #FF006E - Hot Pink
10. #CBFF8C - Lime
```

**Assignment Logic**:
- Color is assigned when a user joins a room session, from `COLORS[color_counter % 10]`
- `color_counter` increments on every join and never decreases, so a user who rejoins does not collide with an existing color
- Because the counter wraps, colors repeat once more than 10 users have joined the session; there is no maximum number of users per room
- Color is ephemeral — not persisted, reassigned on rejoin

---

## Client State

### 5. Browser Storage

User's local profile cache.

**Format**: JSON in `localStorage`

**Key**: `bingopoker_user`

**Value**:
```json
{
  "user_id": "9f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f",
  "email": "alice@company.com",
  "username": "Alice Johnson",
  "role": "observer"
}
```

The client also keeps a transient `sessionColor` on the in-memory user object once the room state arrives; it is written back to `localStorage` alongside the profile.

**Operations**:
- **Set**: On user registration, role toggle, or profile refresh
- **Get**: On page load to check if the user is already registered
- **Clear**: On logout, or when the stored JSON cannot be parsed

Records saved before user IDs existed are upgraded automatically by re-fetching the profile via `GET /api/user/{email}`.

**`sessionStorage`**: key `pending_room` holds a room ID from an invite link (`?r={room_id}`) while the user logs in, so they can be redirected into the room afterwards.

---

## Message Formats

### 6. WebSocket Message Structure

All WebSocket messages follow this structure:

**Base Format**:
```json
{
  "type": "string",
  "payload": { }
}
```

There is no `room_id`, `user_email`, or `timestamp` field — the room and user are bound to the WebSocket connection URL.

**Message Types**:

#### a. `bingo_select` (Client → Server)
```json
{ "type": "bingo_select", "payload": { "row": 0, "col": 2 } }
```

#### b. `poker_select` (Client → Server)
```json
{ "type": "poker_select", "payload": { "value": "8" } }
```

#### c. `reveal` (Client → Server)
```json
{ "type": "reveal", "payload": {} }
```

#### d. `reset` (Client → Server)
```json
{ "type": "reset", "payload": {} }
```

#### e. `room_state` (Server → Joining client only)
```json
{
  "type": "room_state",
  "payload": {
    "config": { "room_id": "room-abc123xy", "name": "Sprint 42", "config": { "grid": [] }, "created_at": "...", "created_by": "9f1c..." },
    "session": {
      "users": [{ "user_id": "9f1c...", "email": "...", "username": "...", "role": "worker", "color": "#E63946" }],
      "bingo_selections": { "alice@company.com": [[0, 2], [1, 3]] },
      "poker_selections": { "alice@company.com": "8" },
      "revealed": false,
      "color_counter": 1
    }
  }
}
```

#### f. `user_joined` / `user_left` (Server → Broadcast)
```json
{ "type": "user_joined", "payload": { "users": [{ "user_id": "9f1c...", "email": "...", "username": "...", "role": "worker", "color": "#E63946" }] } }
```

`user_left` carries the same full `users` list plus the departing `email`.

#### g. `bingo_updated` (Server → Broadcast)
```json
{ "type": "bingo_updated", "payload": { "bingo_selections": { "alice@company.com": [[0, 2]] } } }
```

#### h. `poker_updated` (Server → Broadcast)
```json
{ "type": "poker_updated", "payload": { "email": "alice@company.com", "has_selection": true } }
```

#### i. `revealed` (Server → Broadcast)
```json
{
  "type": "revealed",
  "payload": {
    "bingo_selections": { "alice@company.com": [[0, 2]] },
    "poker_selections": { "alice@company.com": "8" }
  }
}
```

#### j. `round_reset` (Server → Broadcast)
```json
{ "type": "round_reset", "payload": {} }
```

#### k. `replaced` (Server → Displaced client)
```json
{ "type": "replaced", "payload": {} }
```

#### l. `error` (Server → Offending client)
```json
{ "type": "error", "payload": { "message": "Invalid JSON" } }
```

---

## Data Validation Rules

### User Data
- **Email**: Must match `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`; unique across the system (by hash)
- **Username**: 1–50 characters
- **Role**: `worker` or `observer`
- **Color**: Not stored — assigned per session from the 10-color palette

### Room Data
- **Room ID**: `room-` plus 8 alphanumeric characters, URL-safe
- **Room Name**: 1–100 characters, unique among existing rooms
- **Grid**: Exactly 5×5 array of strings
- **Grid Text**: No backend length limit; the frontend editor caps inputs at 50 characters

### Session Data
- **Cell Coordinates**: Row and column integers in 0–4
- **Poker Value**: One of 9 predefined values
- **User Count**: No maximum per room

---

## Storage Initialization

### Default `users.json`
If the file doesn't exist, an empty object is created:
```json
{}
```

### Default `rooms.json`
If the file doesn't exist, an empty object is created:
```json
{}
```

### `backend/data/.email_pepper`
Created on first run when `EMAIL_HASH_PEPPER` is not set. Losing this file makes existing `email_hash` values unmatchable, effectively orphaning all accounts.

---

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8081` | Listen port |
| `DEBUG` | `False` | Enables the `/api/debug/*` data-wiping endpoints |
| `DATA_DIR` | `backend/data` | Where `users.json`, `rooms.json`, and `.email_pepper` live; relative paths resolve against `backend/` |
| `EMAIL_HASH_PEPPER` | auto-generated | HMAC pepper used for email hashing |

Logs are written to `backend/logs/bingopoker.log`.

---

## Migrations Performed at Startup

- **Users**: `UserManager.load()` converts email-keyed records (or records missing `email_hash`) into `user_id`-keyed records with a hashed email, then rewrites `users.json`
- **Rooms**: `RoomManager.migrate_creator_ids()` replaces any `created_by` value containing `@` with the matching user ID, or `null` when the creator is no longer registered
- **Sessions**: sessions created before `color_counter` existed get the counter seeded from the current user count on the next join

---

*Last Updated: 2026-08-18*
