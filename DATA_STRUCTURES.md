# Data Structures - BingoPoker

## Overview

BingoPoker uses two primary JSON files for persistence and several in-memory structures for active room state.

---

## File-Based Storage

### 1. `backend/data/users.json`

Persistent user registry. Stores user profiles only — no color or timestamps.

**Location**: `backend/data/users.json`

**Schema**:
```json
{
  "[email]": {
    "username": "string",
    "role": "worker | observer"
  }
}
```

**Example**:
```json
{
  "alice@company.com": {
    "username": "Alice Johnson",
    "role": "observer"
  },
  "bob@company.com": {
    "username": "Bob Smith",
    "role": "worker"
  },
  "carol@company.com": {
    "username": "Carol White",
    "role": "worker"
  }
}
```

**Operations**:
- **Read**: Load all users on startup
- **Write**: When new user registers
- **Update**: When user updates their username
- **Delete**: No automatic deletion (manual cleanup)

**Constraints**:
- Email is immutable (primary key)
- Username can be updated by user
- Role set at registration; `worker` (developer/tester) or `observer` (PO/stakeholder)
- Color is **not stored** — assigned per room session at join time

---

### 2. `backend/data/rooms.json`

Persistent room configurations. Stores bingo card setup and room metadata.

**Location**: `backend/data/rooms.json`

**Schema**:
```json
{
  "[room_id]": {
    "name": "string",
    "created_at": "string (ISO 8601 timestamp)",
    "created_by": "string (email)",
    "config": {
      "grid": [
        ["string", "string", "string", "string", "string"],
          ["string", "string", "string", "string", "string"],
          ["string", "string", "string", "string", "string"],
          ["string", "string", "string", "string", "string"],
          ["string", "string", "string", "string", "string"]
      ]
    }
  }
}
```

**Example**:
```json
{
  "room-abc123": {
    "name": "Sprint 42 Planning",
    "created_at": "2026-08-12T10:00:00Z",
    "created_by": "alice@company.com",
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
  "room-def456": {
    "name": "Design Sprint 2026",
    "created_at": "2026-08-11T14:30:00Z",
    "created_by": "bob@company.com",
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
- Generated as: `room-{random_8char_alphanumeric}`
- Example: `room-abc123xy`, `room-xyz9876`
- Should be URL-safe

**Special Grid Cell**:
- Center cell (2,2) gets a distinct text color in the UI but otherwise behaves identically to all other cells
- The center cell text is defined in the grid config like any other cell

**Operations**:
- **Read**: On room join or page load
- **Write**: When room is created
- **Update**: When room configuration is edited (if feature added)
- **Delete**: Manual cleanup (old rooms can accumulate)

**Constraints**:
- 5x5 grid is fixed
- Room name can be customized
- Grid text is user-defined
- Room ID is immutable

---

## In-Memory Structures (Runtime)

### 3. Room Session State

Active room state stored in server memory. Lost when room becomes empty.

**Structure**:
```python
{
  "room_id": "string",
  "name": "string",
  "config": { ... },  # From rooms.json
  "state": {
    "users": [
      {
        "email": "string",
        "username": "string",
        "role": "worker | observer",
        "color": "string (hex, assigned at join time in rolling order)"
      },
      ...
    ],
    "bingo_selections": {
      "[user_email]": [[row, col], ...]  # List of [row, col] pairs (0-4 each)
    },
    "poker_selections": {
      "[user_email]": "8"  # One of: "0", "1", "2", "3", "5", "8", "13", "21", "split"
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

**Cell Coordinates**: Row and column indices 0–4.
Cell [2][2] is the center cell (`¯\_(ツ)_/¯` in the default grid).

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

20 colors for user identification, assigned in rolling order.

**List**:
```
1.  #FF6B6B - Red
2.  #4ECDC4 - Teal
3.  #45B7D1 - Blue
4.  #FFA07A - Light Salmon
5.  #98D8C8 - Mint
6.  #F7DC6F - Yellow
7.  #BB8FCE - Purple
8.  #85C1E2 - Light Blue
9.  #F8B195 - Orange
10. #C7CEEA - Lavender
11. #FF85B3 - Pink
12. #64DDAA - Emerald
13. #FFD23F - Bright Yellow
14. #3D5A80 - Navy
15. #C1666B - Dusty Red
16. #48A9A6 - Teal Green
17. #E4C1F9 - Light Purple
18. #F4A261 - Burnt Orange
19. #2A9D8F - Dark Teal
20. #E76F51 - Rust
```

**Assignment Logic**:
- Color is assigned when a user joins a room session
- First user to join gets color 0, second gets color 1, etc.
- Colors wrap around after 20 users
- Color is ephemeral — not persisted, recalculated on rejoin

---

## Client State

### 5. Browser Local Storage

User's local profile cache (browser storage).

**Format**: JSON in `localStorage`

**Key**: `bingopoker_user`

**Value**:
```json
{
  "email": "alice@company.com",
  "username": "Alice Johnson",
  "role": "observer"
}
```

**Operations**:
- **Set**: On user registration or profile update
- **Get**: On page load to check if user is already registered
- **Clear**: Optional logout functionality

---

## Message Formats

### 6. WebSocket Message Structure

All WebSocket messages follow this structure:

**Base Format**:
```json
{
  "type": "string",
  "room_id": "string",
  "timestamp": "string (ISO 8601)",
  ...other fields
}
```

**Message Types**:

#### a. `join` (Client → Server)
```json
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
    "config": { "name": "Sprint 42", "config": { "grid": [[...]] }, ... },
    "session": {
      "users": [{ "email": "...", "username": "...", "role": "worker", "color": "#FF6B6B" }],
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
{ "type": "user_joined", "payload": { "users": [{ "email": "...", "username": "...", "role": "worker", "color": "#FF6B6B" }] } }
```

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
```

#### k. `revealed` (Server → Broadcast)
```json
{
  "type": "revealed",
  "room_id": "room-abc123",
  "selections": {
    "bingo": {
      "alice@company.com": [0, 5, 12],
      "bob@company.com": [0, 6, 12, 18, 24]
    },
    "poker": {
      "alice@company.com": "8",
      "bob@company.com": "13"
    }
  }
}
```

#### l. `round_reset` (Server → Broadcast)
```json
{
  "type": "round_reset",
  "room_id": "room-abc123"
}
```

---

## Data Validation Rules

### User Data
- **Email**: Valid email format, unique across system
- **Username**: 1-50 characters, alphanumeric + spaces/hyphens
- **Color**: Not stored — assigned per-session from a 10-color palette

### Room Data
- **Room ID**: 12 characters, alphanumeric, URL-safe
- **Room Name**: 1-100 characters
- **Grid**: Exactly 5×5 array of strings
- **Grid Text**: 1-50 characters per cell

### Session Data
- **Cell Index**: 0-24 integer
- **Poker Value**: One of 9 predefined values
- **User Count**: Max 10 per room

---

## Storage Initialization

### Default `users.json`
If file doesn't exist, create empty object:
```json
{}
```

### Default `rooms.json`
If file doesn't exist, create empty object:
```json
{}
```

---

## Migration Considerations

For future versions:
- Track data schema version in file header
- Implement migration scripts if structure changes
- Back up JSON files before migrations
- Timestamp-based versioning for audit trail

---

*Last Updated: 2026-08-12*
