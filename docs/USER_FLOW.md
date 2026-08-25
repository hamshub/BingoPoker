# User Flow Documentation - BingoPoker

## Overview

This document describes the step-by-step user interactions and UI flows for the BingoPoker application.

---

## Flow 1: First-Time User Registration

### Scenario: User visits app for first time on a new device/browser

```
User visits http://localhost:8081
        ↓
Browser checks localStorage for 'bingopoker_user'
        ↓
No data found (first time)
        ↓
App shows the room list screen in the background with a login modal overlay on top
        ├─ Field: Email (text input)
        ├─ Field: Username (text input)
        ├─ Field: Role (select: Worker | Observer)
        └─ Button: "Join BingoPoker"
        ↓
User enters email, username, and role
        ↓
User clicks "Join BingoPoker"
        ↓
[CLIENT] Validate inputs
        ├─ Both fields must be non-empty (email format enforced by the input type)
        └─ Username input is capped at 50 characters
        ↓
If validation fails:
        └─ Show error message, stay on form
        ↓
If validation passes:
        ↓
[CLIENT] Request: POST /api/user
        ├─ Body: { email, username, role }
        └─ Returns: { user: { user_id, email, username, role }, is_new: bool }
        ↓
[SERVER] Check if user exists
        ├─ If exists: Return existing profile (role from request is ignored)
        └─ If new: Generate a random user ID, store the hashed email in users.json,
           and return the new profile
        ↓
[CLIENT] Receive response
        ├─ Save to localStorage under 'bingopoker_user': { user_id, email, username, role }
        ├─ Set app state: currentUser = the returned profile
        └─ Hide login modal
        ↓
Room list screen is now interactive
        ├─ Active rooms list (top)
        ├─ Create New Room form (middle)
        ├─ Informational block about the app (bottom)
        └─ Display current username in header badge
```

**Note**: There is no password. The email is never stored in plain text — the server keeps only an HMAC digest of it, keyed by a random user ID.

**Note**: A per-session **color** is not assigned or stored at registration — it is assigned by the server only when the user joins a specific room (see Flow 4), and is never persisted to `users.json`.

### UI Components
- Modal overlay (centered, blurred backdrop) over the room list screen
- Form inputs with validation
- Error messages below fields
- Role dropdown (Worker / Observer)

---

## Flow 2: Returning User

### Scenario: User revisits on same device/browser

```
User visits http://localhost:8081
        ↓
[CLIENT] Check localStorage for 'bingopoker_user'
        ↓
Data found: { user_id, email, username, role }
        ↓
App uses the cached profile and skips the login modal entirely
        ↓
If the cached profile has no user_id (saved before user IDs existed):
        └─ Refresh it from GET /api/user/{email} and re-save to localStorage
        ↓
Load directly to room list screen
        ├─ Show saved username in header badge
        └─ If a room ID is present in the URL (?r=...) or was pending from a shared link, auto-join that room
```

**Note**: Beyond the one-time `user_id` backfill above, the cached `localStorage` profile is used as-is until the user logs out.

### UI Components
- User badge in header showing username
- Role toggle button (Worker / Observer) — swapping persists via `PUT /api/user/{email}`
- "Logout" button (clears `localStorage`, closes any WebSocket, resets the URL to `/`, shows the login modal again — no confirmation prompt)

---

## Flow 3: Create New Room

### Scenario: User creates a new room with custom bingo card

```
User is on room selection screen
        ↓
User fills the "Create New Room" form (no modal — it's inline on the room list screen)
        ├─ Field: Room Name (text input, 1-100 chars)
        └─ Bingo Grid Template: "Use Default", "Custom Grid", or "Import JSON"
        ↓
User enters room name
        ↓
If "Custom Grid" or "Import JSON" chosen, the 5×5 grid editor appears and the user fills/reviews 25 cells
        ├─ Each cell: up to 50 characters; empty cells fall back to "Cell {row}-{col}"
        ├─ "Import JSON" accepts either a bare 5×5 array or an object with a "grid" key
        └─ The center cell (2,2) has no special rule — it's a normal editable cell, just styled differently in the game view
        ↓
User clicks "Create Room"
        ↓
[CLIENT] Validate inputs
        ├─ Room name: non-empty
        └─ Imported grid: must be exactly 5×5
        ↓
If validation fails:
        └─ Show error, stay on form
        ↓
If validation passes:
        ↓
[CLIENT] Request: POST /api/room
        ├─ Body: { 
        │     name: "string",
        │     created_by: "email",
        │     grid: [[...], [...], [...], [...], [...]]
        │   }
        └─ Returns: { room_id: "room-abc123XY", message: "Room created successfully" }
        ↓
[SERVER] Validate name/grid, resolve creator email to a user ID
        ├─ Reject with 409 if a room with the same name already exists
        ├─ Reject with 404 if the creator is not a registered user
        ├─ Generate room_id and save to rooms.json (created_by stores the user ID)
        └─ Create empty in-memory session state
        ↓
[CLIENT] Receive response
        ├─ Reload the rooms list
        ├─ Auto-join the new room
        └─ Connect WebSocket to /ws/{room_id}/{email}
        ↓
Room screen loads with:
        ├─ Bingo card grid (25 cells)
        ├─ Room name and copyable invite link (built client-side from location.origin + ?r={room_id})
        ├─ "Download Config" button that exports the grid as JSON in the same shape the import accepts
        ├─ Current user info (username, session color — assigned on join, see Flow 4)
        ├─ Poker card selector (0, 1, 2, 3, 5, 8, 13, 21, split)
        ├─ Reveal All button (ENABLED)
        └─ Reset Round button (DISABLED)
```

### UI Components
- Inline "Create New Room" form on the room list screen (not a modal)
- Text input for room name (max 100 characters)
- Template buttons: Use Default / Custom Grid / Import JSON
- Hidden file input for JSON import
- 5×5 grid editor with text inputs (only shown for Custom Grid / Import JSON)
- Click-to-copy invite link display
- "Remove" button on room cards the current user created (compares `user_id` against the room's `created_by`); confirms before calling `DELETE /api/room/{room_id}`

---

## Flow 4: Join Existing Room

### Scenario: User joins a room (by ID or shared link)

#### Variant 4a: Join by URL Parameter
```
User visits: http://localhost:8081/?r=room-abc123
        ↓
[CLIENT] Parse query parameter: room_id = "room-abc123"
        ↓
If user is not logged in: save room_id to sessionStorage as "pending_room", show login modal first
        ↓
[CLIENT] Request: GET /api/room/room-abc123
        └─ Returns: { room_id, room: { config: {...}, session: {...} } }
        ↓
[SERVER] Load from rooms.json + in-memory session
        ↓
If room not found:
        ├─ [CLIENT] Show error: "Failed to join room"
        └─ Stay on/return to room selection
        ↓
If room found:
        ├─ [CLIENT] Render room screen with config
        └─ [CLIENT] Connect WebSocket to /ws/{room_id}/{email} — there is no separate "join" message; connecting to this URL joins the room
        ↓
[SERVER] Add user to session (assigns next color in the room's rotation), broadcasts "user_joined" to everyone else
        ↓
[CLIENT] Receive "room_state" with current selections
        └─ Render any existing bingo/poker marks
```

#### Variant 4b: Join from the Active Rooms List
```
User is on room selection screen
        ↓
User clicks "Join" on a room card in the Active Rooms list
        ↓
[CLIENT] Request: GET /api/room/{room_id}
        ↓
[SERVER] Load room config
        ↓
If room not found:
        └─ Return 404
        ↓
If room found:
        ├─ [CLIENT] Render room screen
        └─ [CLIENT] Connect WebSocket to /ws/{room_id}/{email}
        ↓
[SERVER] Add user to session
        ├─ There is no hard user limit; colors wrap around after 10 users (see color_palette.py)
        └─ Broadcast "user_joined" (full users list) to everyone else
        ↓
Success: Show room screen
```

### UI Components
- Room screen with:
  - Game header: room name, copyable invite link, "Download Config" button, username badge with session color dot, and "Leave Room" button
  - 5×5 Bingo grid (ready to click) on the left
  - Round Controls (Reveal All / Reset Round) on the right
  - Participant list with colors, role badges, and vote status
  - Poker value buttons (0, 1, 2, 3, 5, 8, 13, 21, split)

---

## Flow 5: Playing a Round - Bingo Selection

### Scenario: User selects cells on the bingo card

```
User is viewing the room
        ↓
User clicks on a bingo cell
        ↓
[CLIENT] Check if room is revealed
        ├─ If revealed: Don't allow changes
        └─ If not revealed: Allow selection
        ↓
If cell is already selected by user:
        ├─ Toggle OFF (deselect)
        └─ Remove marking
        ↓
If cell is not selected:
        ├─ Toggle ON (select)
        └─ Mark with user's color circle
        ↓
[CLIENT] Send WebSocket message "bingo_select"
        ├─ payload: { row: 0-4, col: 0-4 }
        └─ (user is identified by the connection itself, not the message)
        ↓
[SERVER] Receive "bingo_select"
        ├─ Toggle the cell in session.bingo_selections
        └─ Broadcast "bingo_updated" with the full bingo_selections map to all clients in room
        ↓
[CLIENT] All clients receive "bingo_updated"
        ├─ Replace local bingo_selections with the received map
        ├─ Re-render bingo grid
        └─ Show/hide colored dot on that cell
        ↓
Cell now displays:
        ├─ If selected by user: Small colored dot (user's session color)
        ├─ If selected by others: Multiple colored dots (each user's color)
        └─ If not selected: Empty cell
```

**Visibility rule**: an Observer's (PO/stakeholder) selections are always visible to everyone. A Worker's (developer/tester) selections are only visible to themselves until the round is revealed — other workers see nothing on that cell until then.

### UI Components
- 5×5 grid of clickable cells
- Each cell shows:
  - Cell text (from config)
  - Small colored circle(s) in corner indicating selections
  - Hover effect
  - Click feedback (change cursor to pointer)

---

## Flow 6: Playing a Round - Poker Selection

### Scenario: User selects their story point estimate

```
User is viewing the room
        ↓
User clicks on a poker value button
        ├─ Options: 0, 1, 2, 3, 5, 8, 13, 21, split
        ↓
[CLIENT] Check if revealed
        ├─ If revealed: Don't allow change
        └─ If not: Allow selection
        ↓
If user previously selected a value:
        ├─ Deselect old value
        └─ Select new value
        ↓
[CLIENT] Highlight selected poker card
        └─ Visual feedback (border, background color, etc.)
        ↓
[CLIENT] Send WebSocket message "poker_select"
        └─ payload: { value: "0" | "1" | "2" | "3" | "5" | "8" | "13" | "21" | "split" }
        ↓
[SERVER] Receive "poker_select"
        ├─ Overwrite the user's poker_selections entry (hidden from other users)
        └─ Broadcast "poker_updated" { email, has_selection: true } to all users in room
        └─ (payload does NOT include the value — only that a selection was made)
        ↓
[CLIENT] All clients receive "poker_updated"
        ├─ Re-render the participant list
        ├─ Show that user's status as "ready"
        └─ Do NOT show the actual value (hidden until reveal)
        ↓
Poker selector shows:
        ├─ User's own selection highlighted
        ├─ Other users' values hidden ("ready" or "waiting" only)
        └─ All buttons remain clickable until reveal
```

### UI Components
- Poker value button row
- 9 buttons: "0", "1", "2", "3", "5", "8", "13", "21", "split"
- Selected state: highlighted/active styling
- Participant list showing "ready" / "waiting" per user

---

## Flow 7: Reveal Round

### Scenario: User clicks Reveal button to show all selections

```
User is viewing the room (before reveal)
        ↓
User clicks "Reveal All" button
        ├─ Button is ENABLED before reveal
        └─ Button is DISABLED after reveal
        ↓
[CLIENT] Send WebSocket message "reveal"
        └─ payload: {} (no fields — user identified by connection)
        ↓
[SERVER] Receive "reveal"
        ├─ Set session: revealed = true
        ├─ Collect all selections:
        │   ├─ Bingo selections: { email: [[row, col], ...] }
        │   └─ Poker selections: { email: "value" }
        └─ Broadcast "revealed" message with all selections
        ↓
[CLIENT] All clients receive "revealed"
        ├─ Update session state: revealed = true
        └─ Update UI:
            ├─ Freeze the poker buttons (disabled)
            ├─ Freeze the bingo grid (cells no longer clickable)
            ├─ Disable "Reveal All" button
            ├─ Enable "Reset Round" button
            └─ Show every participant's value
        ↓
Display after reveal:
        ├─ Bingo card: every participant's colored dots visible, including workers'
        ├─ Participant list: each user's poker value next to their name and color
        └─ Summary below the participant list:
            ├─ Average of the numeric votes (0–21), one decimal place
            └─ Count of "split" votes, when any were cast
```

### UI Components
- "Reveal All" button: ENABLED before reveal, DISABLED after
- "Reset Round" button: DISABLED before reveal, ENABLED after
- Participant list entries showing username, role badge, color dot, and revealed value
- Average / split summary block
- Bingo grid with all colored dots visible and cells frozen

---

## Flow 8: Reset Round

### Scenario: User clicks Reset button to start new round

```
User is viewing the room (after reveal)
        ↓
User clicks "Reset Round" button
        ├─ Button is DISABLED before reveal
        └─ Button is ENABLED after reveal
        ↓
[CLIENT] Send WebSocket message "reset"
        └─ payload: {}
        ↓
[SERVER] Receive "reset"
        ├─ Clear room state:
        │   ├─ bingo_selections = {}
        │   ├─ poker_selections = {}
        │   └─ revealed = false
        └─ Broadcast "round_reset" message to all in room
        ↓
[CLIENT] All clients receive "round_reset"
        ├─ Clear local state:
        │   ├─ All bingo selections removed
        │   ├─ All poker selections removed
        │   └─ Reset button disabled, Reveal button enabled
        └─ Re-render UI:
            ├─ Clear colored dots from bingo grid and unfreeze the cells
            ├─ Clear poker selections (deselect all buttons) and unfreeze them
            ├─ Remove the average / split summary
            ├─ Disable "Reset Round" button
            └─ Enable "Reveal All" button
        ↓
Ready for new round:
        ├─ Users can click bingo cells again
        ├─ Users can select poker values again
        └─ Anyone can click "Reveal All" again (back to Flow 7)
```

### UI Components
- Same as normal round state

---

## Flow 9: User Joins Mid-Round

### Scenario: New user joins while round is in progress

```
User connects to room via WebSocket at /ws/{room_id}/{email}
        ↓
[SERVER] On connection
        ├─ Validate user and room exist (401/404 otherwise)
        ├─ If the same user already has a connection open in this room, send it "replaced" and close it
        ├─ Add user to session, assigning the next color in the room's rotation (colors wrap after 10 users — no hard room limit)
        └─ Send "room_state" directly to the new connection with:
            ├─ Room config
            ├─ All users currently in room
            ├─ Current bingo selections (worker selections hidden from others until reveal; observer selections always visible)
            ├─ Poker selections (values hidden if not revealed)
            └─ Revealed flag
        ↓
[SERVER] Broadcast "user_joined" (full users list) to everyone else already in the room
        ↓
If room is revealed:
        ├─ [CLIENT] Show all poker selections
        └─ New user can see results immediately
        ↓
If room is not revealed:
        ├─ [CLIENT] Show vote status (who has voted)
        └─ New user can:
            ├─ Select bingo cells
            ├─ Select poker value
            └─ Participate in current round
```

### UI Components
- Participant list updated with the new user, their color, and role badge

---

## Flow 10: User Leaves Room

### Scenario: User disconnects (closes tab, loses connection, etc.)

```
User closes tab / disconnects
        ↓
[SERVER] Detects WebSocket disconnect
        ├─ Remove user from room's user list
        ├─ Keep room state intact (other users continue)
        ├─ If last user leaves:
        │   ├─ Clear room state from memory
        │   └─ Room config remains in rooms.json
        └─ Broadcast "user_left" to remaining users in room
        ↓
[CLIENT] All remaining users receive "user_left"
        ├─ Remove user from the participant list
        └─ Their bingo dots and poker status disappear with the next render
        ↓
Room continues for remaining users:
        ├─ Remaining users' selections persist
        ├─ Can continue playing
        └─ Participant list updates
        ↓
If the same user reconnects:
        └─ They are added to the session again and receive the NEXT color in the
           room's rotation, not their previous one
```

### UI Components
- Updated participant list

---

## Flow 11: Connection Loss

### Scenario: Network disconnect

```
User has stable connection
        ↓
Network connection drops
        ↓
[CLIENT] WebSocket "close" event fires
        └─ appState.ws is set to null; no status banner or retry is shown
        ↓
The user must re-enter the room (or reload) to reconnect,
which re-fetches room state over REST and opens a new WebSocket connection.
```

### UI Components
- None — there is no visible connection-status indicator and no reconnection logic

---

## Flow 12: Leave Room / Logout

### Scenario: User intentionally leaves room or logs out

```
User clicks "Leave Room" button (or uses the browser Back button)
        ↓
[CLIENT] Close WebSocket connection
        ├─ Clear room-specific state (selections, current room)
        └─ Reset the URL to "/" via history.pushState
        ↓
[SERVER] Detects the closed socket
        ├─ Remove user from session
        └─ Broadcast "user_left" to the remaining users
        ↓
[CLIENT] Navigate back to room selection screen and reload the rooms list
        ├─ User profile remains (localStorage intact)
        └─ Option to join another room or create a new one
        ↓
---
        ↓
User clicks "Logout" (room selection screen header)
        ↓
[CLIENT] No confirmation prompt — immediately:
        ├─ Close any open WebSocket
        ├─ Clear localStorage ('bingopoker_user')
        ├─ Reset the URL to "/"
        └─ Show the login modal again
```

### UI Components
- "Leave Room" button (game header)
- "Logout" button (room selection header)
- Browser Back from a room returns to the room list and closes the socket

---

## Error States & Handling

### Common Errors

#### 1. Invalid Email Format
```
User enters: "notanemail"
        ↓
The browser's native email input validation blocks the submit
        ↓
If it reaches the server, POST /api/user returns 400 "Email format is invalid"
        ↓
[CLIENT] Show the server message under the login form
```

#### 2. Room Not Found
```
User opens a link for a deleted or unknown room
        ↓
[SERVER] GET /api/room/{room_id} returns 404 (or 400 for a malformed ID)
        ↓
[CLIENT] alert("Failed to join room: Room {room_id} not found")
        ↓
User stays on the room selection screen
```

#### 3. Duplicate Room Name
```
User creates a room whose name already exists
        ↓
[SERVER] POST /api/room returns 409
        ↓
[CLIENT] Show "A room named '{name}' already exists" under the create form
```

#### 4. Deleting Someone Else's Room
```
Only the creator sees the "Remove" button, but the rule is enforced server-side
        ↓
[SERVER] DELETE /api/room/{room_id} returns 403 for anyone else
        ↓
[CLIENT] alert("Failed to delete room: Only the room creator can delete this room")
```

#### 5. Color Palette Wraparound
```
More than 10 users join the same room
        ↓
[SERVER] get_color_by_index() wraps around (index % 10)
        ↓
Two or more users may end up with the same color — there is no hard room capacity limit or "room full" rejection
```

#### 6. Duplicate Connection (Same User, Same Room)
```
The same email opens the room in a second tab
        ↓
[SERVER] Sends "replaced" to the first socket and closes it
        ↓
[CLIENT] First tab shows: "You joined this room from another tab or window."
```

#### 7. Network Error
```
User WebSocket disconnects
        ↓
[CLIENT] appState.ws is cleared; no status banner is shown
        ↓
The user must re-enter the room or reload the page to reconnect
```

### UI Components
- Inline error message blocks under the login and create-room forms
- `alert()` dialogs for join/delete failures and the "replaced" notice

---

## Developer Tools

Adding `?dev=true` to the URL reveals the dev-only buttons in the login modal:
- "Delete all users" → `DELETE /api/debug/users`, then clears `localStorage` and reloads
- "Delete all rooms" → `DELETE /api/debug/rooms`

These endpoints exist only when the server runs with `DEBUG=true`.

---

*Last Updated: 2026-08-18*
