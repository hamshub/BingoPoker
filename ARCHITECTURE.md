# Architecture Document - BingoPoker

## System Overview

BingoPoker is a real-time collaborative web application using a client-server WebSocket architecture. The system maintains room state on the server and synchronizes it with multiple connected clients.

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser Clients                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Client 1 │  │ Client 2 │  │ Client 3 │  │ Client N │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼───────────┘
        │             │             │             │
        └─────────────┼─────────────┼─────────────┘
                      │ WebSocket
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼──────────────────────────▼─────────┐
│          aiohttp Server (Python)           │
├───────────────────────────────────────────┤
│  ┌─────────────────────────────────────┐ │
│  │    WebSocket Handler                │ │
│  │  - Message routing                  │ │
│  │  - Broadcast logic                  │ │
│  └─────────────────────────────────────┘ │
│                                           │
│  ┌─────────────────────────────────────┐ │
│  │    Room Manager                     │ │
│  │  - Room creation/deletion           │ │
│  │  - State management                 │ │
│  │  - User sessions                    │ │
│  │  - Bingo + Poker selection tracking │ │
│  └─────────────────────────────────────┘ │
│                                           │
│  ┌─────────────────────────────────────┐ │
│  │    User Manager                     │ │
│  │  - User registration                │ │
│  │  - Color assignment                 │ │
│  │  - Profile caching                  │ │
│  └─────────────────────────────────────┘ │
└──────────────┬──────────────────────────┬─┘
               │                          │
               ▼                          ▼
        ┌─────────────┐          ┌─────────────┐
        │  users.json │          │ rooms.json  │
        │ (Persistent)│          │(Persistent) │
        └─────────────┘          └─────────────┘
```

## Component Details

### 1. Frontend (Client-Side)

#### Files
- `index.html` - UI layout with login modal, room list, bingo grid, poker buttons, controls
- `js/app.js` - All application state, screen navigation, and WebSocket message handling
- `js/api.js` - REST API client (`BingoPokerAPI`) and grid utilities (`GridUtils`)
- `css/styles.css` - Dark theme styling (Outfit font, `#057FA8` accent palette)

#### Responsibilities
- User input handling (bingo selection, poker selection)
- WebSocket connection lifecycle (no automatic reconnection currently implemented)
- Real-time UI updates based on server messages
- Local user profile caching (`localStorage`: email, username, role)
- Visual rendering of:
  - Bingo card grid with user color dots
  - Poker selections with names and values
  - Room information and shareable invite link

### 2. Backend (Server-Side)

#### Main Application (`app.py`)
- HTTP endpoints for:
  - `GET /` - Serve `index.html`
  - `GET /health` - Health check
  - `POST /api/user`, `GET /api/user/{email}`, `PUT /api/user/{email}` - User registration/profile
  - `POST /api/room`, `GET /api/room/{room_id}`, `GET /api/rooms` - Room create/get/list
  - `GET /ws/{room_id}/{user_email}` - WebSocket endpoint (room and user bound to the connection)
  - `/css`, `/js`, `/templates` - Static file serving

- WebSocket handler (`handlers/websocket.py`) for:
  - Client connections/disconnections
  - Message routing and broadcasting
  - State synchronization

#### Room Manager (`utils/room_manager.py`)
Manages in-memory room state and persistence:
- **Room Structure**:
  - `room_id` (generated, `room-{8 alphanumeric}`)
  - `name` (display name)
  - `config.grid` (5x5 bingo card text)
  - `created_at`, `created_by`
  - Session (in-memory, ephemeral, keyed separately by `room_id`):
    - `users` (current connections, each with assigned `color`)
    - `bingo_selections` (user → list of `[row, col]` pairs)
    - `poker_selections` (user → poker value)
    - `revealed` (boolean)
    - `color_counter` (monotonic, never reused within a room)

- **Methods**:
  - `create_room(name, grid, created_by)` → (success, error, room_data)
  - `get_room(room_id)` → persisted config
  - `get_room_state(room_id)` → config + session combined
  - `add_user_to_session(room_id, email, user_data)` → bool
  - `remove_user_from_session(room_id, email)` → bool
  - `record_bingo_selection(room_id, email, row, col)` → (success, error) — toggles the cell
  - `record_poker_selection(room_id, email, value)` → (success, error)
  - `reveal_round(room_id)` → (success, error)
  - `reset_round(room_id)` → (success, error)
  - `get_active_rooms()` → all persisted room configs

#### User Manager (`utils/user_manager.py`)
Manages user profiles:
- **User Structure**:
  - `email` (unique identifier)
  - `username`
  - `role` (`"worker"` or `"observer"`)

- **Methods**:
  - `register_user(email, username, role)` → (success, error, user_profile)
  - `get_user(email)` → user data
  - `user_exists(email)` → boolean
  - `update_username(email, new_username)` → (success, error)

#### Color Palette (`utils/color_palette.py`)
10-color palette with rolling assignment per room session:
- Predefined list of 10 maximally contrasted hex colors
- Color assigned at join time using a monotonic per-room counter (1st join = color 0, 2nd = color 1, ...); rejoining users get the **next** color in sequence, not their original one
- If more than 10 users join a room, colors wrap around and repeat
- Color is ephemeral — never persisted to `users.json`

### 3. Data Persistence

#### `users.json`
```json
{
  "user@example.com": {
    "email": "user@example.com",
    "username": "John Doe",
    "role": "worker"
  },
  "user2@example.com": {
    "email": "user2@example.com",
    "username": "Jane Smith",
    "role": "observer"
  }
}
```

#### `rooms.json`
```json
{
  "room-abc123": {
    "room_id": "room-abc123",
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
    "created_at": "2026-08-12T10:00:00Z",
    "created_by": "user@example.com"
  }
}
```

## WebSocket Message Protocol

See [API_SPECIFICATIONS.md](API_SPECIFICATIONS.md#websocket-messages) for the full, accurate message catalogue (envelope format, payload shapes, and every message type). Summary: clients connect directly to `/ws/{room_id}/{user_email}` (no separate "join" message), and every message uses `{ "type": "...", "payload": {...} }`.

## Data Flow Sequences

### Initial Room Load
```
Client → GET /api/room/{room_id} → Server
↓
Server loads config + in-memory session from rooms.json / sessions dict
↓
Server → 200 OK + { room_id, room: { config, session } }
↓
Client opens WebSocket to /ws/{room_id}/{user_email}
↓
Server adds user to session, sends "room_state" to the joining client
↓
Server broadcasts "user_joined" (full users list) to everyone else
↓
Client renders UI with current state
```

### Bingo Selection
```
User clicks bingo cell
↓
Client → WebSocket "bingo_select" { row, col }
↓
Server toggles the cell in session.bingo_selections
↓
Server broadcasts "bingo_updated" (full bingo_selections map) to all clients in room
↓
All clients update UI to show colored dot on cell
```

### Reveal Vote
```
User clicks "Reveal" button
↓
Client → WebSocket "reveal" message
↓
Server sets session.revealed = true
↓
Server broadcasts "revealed" with bingo_selections + poker_selections
↓
All clients render:
  - Bingo grid with color dots (worker selections now visible to all)
  - Poker values shown next to each participant
  - Reveal button disabled, Reset button enabled
```
Client → WebSocket "reveal" message
↓
Server sets room state: revealed = true
↓
Server broadcasts "revealed" with all selections
↓
All clients render:
  - Bingo grid with color circles
  - Poker values with usernames in center area
  - Reveal button disabled, Reset button enabled
```

## Room State Management

### Normal Flow (Before Reveal)
```
Reveal Button: ENABLED
Reset Button: DISABLED
Poker Selections: Hidden
Bingo: User can select/deselect cells
```

### After Reveal
```
Reveal Button: DISABLED
Reset Button: ENABLED
Poker Selections: Visible with color coding
Bingo: Display colors for each selection
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
- No automatic reconnection is implemented; if the WebSocket closes, the user must navigate back into the room to reconnect
- The server does not buffer or queue messages during a disconnection

### Color Palette Wraparound (10 colors)
- There is no hard user limit; if more than 10 users join a room, colors wrap around and repeat (`get_color_by_index` uses modulo)

### Invalid Room ID
- Return 404 with JSON error
- Prompt user to create new room or enter valid ID

### Malformed Messages
- Server validates JSON structure and message `type`
- Unknown `type` or invalid JSON returns an `error` message to the sender
- Other invalid payloads (e.g. bad poker value) are currently silently ignored

## Performance Considerations

- In-memory room state for active rooms
- Lazy-load room configs from JSON
- Broadcast only to clients in specific room (not all connections)
- Limit bingo grid to 25 cells (fixed)
- Limit poker values to 9 options (fixed)
- Cleanup room state when last user leaves

---

*Last Updated: 2026-08-12*
