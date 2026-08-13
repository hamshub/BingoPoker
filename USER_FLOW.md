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
        ├─ Email must be valid format
        └─ Username must be 1-50 characters
        ↓
If validation fails:
        └─ Show error message, stay on form
        ↓
If validation passes:
        ↓
[CLIENT] Request: POST /api/user
        ├─ Body: { email, username, role }
        └─ Returns: { user: { email, username, role }, is_new: bool }
        ↓
[SERVER] Check if user exists
        ├─ If exists: Return existing profile (role from request is ignored)
        └─ If new: Save to users.json, return new profile
        ↓
[CLIENT] Receive response
        ├─ Save to localStorage: { email, username, role }
        ├─ Set app state: currentUser = { email, username, role }
        └─ Hide login modal
        ↓
Room list screen is now interactive
        ├─ Active rooms list (top)
        ├─ Create New Room form (bottom)
        └─ Display current username in header badge
```

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
Data found: { email, username, role }
        ↓
App trusts the cached profile and skips the login modal entirely
        ↓
Load directly to room list screen
        ├─ Show saved username in header badge
        └─ If a room ID is present in the URL (?r=...) or was pending from a shared link, auto-join that room
```

**Note**: There is currently no server-side re-validation call (e.g. `GET /api/user/{email}`) on return visits — the cached `localStorage` profile is used as-is until the user logs out.

### UI Components
- User badge in header showing username
- "Logout" button (clears `localStorage`, closes any WebSocket, shows the login modal again — no confirmation prompt)

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
If "Custom Grid" or "Import JSON" chosen, user fills/reviews 25 bingo card cells
        ├─ Each cell: up to 50 characters
        └─ The center cell (2,2) has no special rule — it's a normal editable cell, just styled with a different text color in the UI
        ↓
User clicks "Create Room"
        ↓
[CLIENT] Validate inputs
        ├─ Room name: non-empty, ≤100 chars
        └─ Grid: exactly 5×5
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
        └─ Returns: { room_id: "room-abc123", message: "Room created successfully" }
        ↓
[SERVER] Generate room_id
        ├─ Reject with 409 if a room with the same name already exists
        ├─ Save to rooms.json
        └─ Create in-memory room state
        ↓
[CLIENT] Receive response
        ├─ Navigate to room view
        └─ Connect WebSocket to /ws/{room_id}/{email}
        ↓
Room screen loads with:
        ├─ Bingo card grid (25 cells)
        ├─ Room name and copyable invite link (built client-side from location.origin + ?r={room_id})
        ├─ Current user info (username, session color — assigned on join, see Flow 4)
        ├─ Poker card selector (0, 1, 2, 3, 5, 8, 13, 21, Split)
        ├─ Reveal button (ENABLED)
        └─ Reset button (DISABLED)
```

### UI Components
- Inline "Create New Room" form on the room list screen (not a modal)
- Text input for room name
- Template buttons: Use Default / Custom Grid / Import JSON
- 5×5 grid editor with text inputs (only shown for Custom Grid / Import JSON)
- Click-to-copy invite link display

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
```

### UI Components
- Room screen with:
  - Room name and ID at top
  - 5×5 Bingo grid (ready to click)
  - User list (with colors) on side panel
  - Poker selector (buttons or cards)
  - Reveal and Reset buttons
  - Status bar (Connected/Disconnected)

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
User clicks on a poker value button/card
        ├─ Options: 0, 1, 2, 3, 5, 8, 13, 21, Split
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
        ├─ Update local state
        ├─ Show indicator: "Estimate received from {username}"
        └─ Do NOT show the actual value (hidden until reveal)
        ↓
Poker selector shows:
        ├─ User's own selection highlighted
        ├─ Other users' values hidden (just show "Vote pending")
        └─ All buttons remain clickable until reveal
```

### UI Components
- Poker value selector (cards or buttons layout)
- 9 buttons: "0", "1", "2", "3", "5", "8", "13", "21", "Split"
- Selected state: highlighted/active styling
- Vote status indicator showing which users have voted

---

## Flow 7: Reveal Round

### Scenario: User clicks Reveal button to show all selections

```
User is viewing the room (before reveal)
        ↓
User clicks "Reveal" button
        ├─ Button is ENABLED before reveal
        └─ Button is DISABLED after reveal
        ↓
[CLIENT] Send WebSocket message "reveal"
        └─ payload: {} (no fields — user identified by connection)
        ↓
[SERVER] Receive "reveal"
        ├─ Set room state: revealed = true
        ├─ Collect all selections:
        │   ├─ Bingo selections: { email: [[row, col], ...] }
        │   └─ Poker selections: { email: "value" }
        └─ Broadcast "revealed" message with all selections
        ↓
[CLIENT] All clients receive "revealed"
        ├─ Update room state: revealed = true
        ├─ Update UI:
        │   ├─ Disable poker selector (can't change)
        │   ├─ Disable bingo selection (can't click cells)
        │   ├─ Disable "Reveal" button
        │   ├─ Enable "Reset" button
        │   └─ Show all selections with usernames
        ↓
Display after reveal:
        ├─ Bingo card: All colored circles visible (multiple if overlapped)
        ├─ Center area: List of all poker selections
        │   ├─ Format: "{Username}: {Value}" with color coding
        │   ├─ Sort by value (0→21 then Split)
        │   └─ Show user's assigned color next to name
        └─ Analysis (optional):
            ├─ Highest estimate
            ├─ Lowest estimate
            └─ Count of "Split" votes
```

### UI Components
- "Reveal" button: ENABLED before reveal, DISABLED after
- "Reset" button: DISABLED before reveal, ENABLED after
- Poker results display:
  - Each user's value with:
    - Username
    - Value
    - User's color indicator
  - Sorted/grouped by value
- Bingo grid with all colored circles visible
- Connection status indicator

---

## Flow 8: Reset Round

### Scenario: User clicks Reset button to start new round

```
User is viewing the room (after reveal)
        ↓
User clicks "Reset" button
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
            ├─ Clear colored circles from bingo grid
            ├─ Clear poker selections (deselect all buttons)
            ├─ Clear poker results display
            ├─ Disable "Reset" button
            └─ Enable "Reveal" button
        ↓
Ready for new round:
        ├─ Users can click bingo cells again
        ├─ Users can select poker values again
        └─ Users can click "Reveal" again (back to Flow 7)
```

### UI Components
- Same as normal round state
- Smooth transition (clear visuals)
- Confirmation/success indicator

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
- Join notification (toast/banner)
- Updated user list showing new user
- User's color displayed

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
        ├─ Remove user from user list display
        ├─ Remove user's colored circles from bingo grid
        ├─ Remove user's poker selection from results
        └─ Show notification: "{Username} left the room"
        ↓
Room continues for remaining users:
        ├─ Selections persist
        ├─ Can continue playing
        └─ User list updates
        ↓
If user reconnects:
        ├─ Same user (email) reconnecting?
        └─ Get their color again, rejoin as same user
```

### UI Components
- Notification when user leaves
- Updated user list
- Visual feedback (fade/remove user entry)

---

## Flow 11: Connection Loss & Reconnection

### Scenario: Network disconnect and reconnect

> **Not currently implemented** — there is no automatic reconnection logic. This describes the intended future behavior only.

```
User has stable connection
        ↓
Network connection drops
        ↓
[CLIENT] WebSocket "close" event fires
        └─ appState.ws is set to null; no status banner or retry is currently shown
        ↓
Today, the user must navigate back into the room (or reload) to reconnect,
which re-fetches room state over REST and opens a new WebSocket connection.
```

### UI Components (current)
- None — there is no visible connection-status indicator

### UI Components (future / not yet built)
- Connection status indicator (top right)
- Automatic retry with backoff
- "Reconnect" button on persistent failure

---

## Flow 12: Leave Room / Logout

### Scenario: User intentionally leaves room or logs out

```
User clicks "Leave Room" button
        ↓
[CLIENT] Close WebSocket connection
        ├─ Send disconnect signal to server
        └─ Clear room-specific data
        ↓
[SERVER] Process disconnect
        └─ Remove user from room
        ↓
[CLIENT] Navigate back to room selection screen
        ├─ User profile remains (localStorage intact)
        └─ Option to join another room or create new room
        ↓
---
        ↓
User clicks "Logout" (optional feature)
        ↓
[CLIENT] Confirm action: "Clear profile?"
        ↓
If confirmed:
        ├─ Clear localStorage
        ├─ Close WebSocket
        ├─ Navigate to registration screen
        └─ User starts fresh on next visit
        ↓
If cancelled:
        └─ Return to previous screen
```

### UI Components
- "Leave Room" button (in room view)
- "Logout" button (in settings/menu)
- Confirmation dialog
- Back to main menu

---

## Error States & Handling

### Common Errors

#### 1. Invalid Email Format
```
User enters: "notanemail"
        ↓
[CLIENT] Validation fails
        ↓
Show error: "Please enter a valid email address"
```

#### 2. Room Not Found
```
User joins: room-invalid123
        ↓
[SERVER] Room not in rooms.json
        ↓
[CLIENT] Show error: "Room not found. Check the room ID and try again."
        ↓
Offer options:
        ├─ Create new room
        └─ Try another room ID
```

#### 3. Color Palette Wraparound
```
More than 10 users join the same room
        ↓
[SERVER] get_color_by_index() wraps around (index % 10)
        ↓
Two or more users may end up with the same color — there is no hard room capacity limit or "room full" rejection
```

#### 4. Network Error
```
User WebSocket disconnects
        ↓
[CLIENT] Show status: "Disconnected"
        ↓
Auto-retry or manual "Reconnect" button
```

### UI Components
- Error modals/toasts
- Error banners with dismiss button
- Contextual help text
- Retry options

---

## Accessibility & Mobile Considerations

### Responsive Design
- Bingo grid scales for mobile (smaller screens)
- Poker selector adapts to screen size (horizontal scroll or wrapping)
- User list collapses to side drawer on mobile
- Touch-friendly button sizes (min 48px)

### Keyboard Navigation
- Tab through bingo cells
- Tab through poker buttons
- Enter/Space to select
- Escape to close modals

### Color Accessibility
- Colored circles supplemented with user initials or small text
- High contrast between colors
- Color-blind friendly palette option (future)

### Offline Support (Optional Future)
- ServiceWorker for offline detection
- Queue actions if offline
- Sync when reconnected

---

*Last Updated: 2026-08-12*
