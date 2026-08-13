# BingoPoker Implementation Task List

## Overview
Implementation using Copilot-driven development with user oversight. Tasks are scoped for manageable context windows with separate, focused files. User only codes when necessary.

> **Note**: This is the original task-planning document. The actual implementation diverged from some details below as the project evolved — e.g. there is no "FREE"/locked center cell (it's a normal editable cell with a distinct text color), room joining uses `?r=` not `?room=`, there's no separate WebSocket "join" message (the room/user are bound to the `/ws/{room_id}/{user_email}` URL), and several validators listed here (`validate_cell_text`, `validate_cell_index`) were never implemented or were later removed. See [API_SPECIFICATIONS.md](API_SPECIFICATIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md), and [DATA_STRUCTURES.md](DATA_STRUCTURES.md) for the current, accurate behavior.

---

## Phase 1: Backend Core + Room Creation

### Backend Infrastructure

#### Task 1.1: Project Setup & Dependencies
**Status**: Not Started  
**File**: `backend/requirements.txt`  
**Scope**: ~20 lines  
**Dependencies**: None  
**Description**: Define all Python dependencies for backend  
**Deliverables**:
- requirements.txt with aiohttp, aiofiles, python-dotenv, pytest, pytest-aiohttp

---

#### Task 1.2: ColorPalette Utility
**Status**: Not Started  
**File**: `backend/utils/color_palette.py`  
**Scope**: ~100 lines  
**Dependencies**: None  
**Description**: 20-color palette with rolling assignment logic  
**Deliverables**:
- ColorPalette class with:
  - COLORS list (20 hex colors)
  - assign_color(room_id, used_colors) → color
  - get_available_colors(room_id, used_colors) → [colors]
  - Recycle logic when users leave

---

#### Task 1.3: Validators Utility
**Status**: Not Started  
**File**: `backend/utils/validators.py`  
**Scope**: ~150 lines  
**Dependencies**: None  
**Description**: Input validation functions for all user inputs  
**Deliverables**:
- Validators class with static methods:
  - validate_email(email) → bool
  - validate_username(username) → bool
  - validate_room_name(name) → bool
  - validate_grid(grid) → bool (5x5, center = "FREE")
  - validate_cell_text(text) → bool
  - validate_cell_index(cell) → bool
  - validate_poker_value(value) → bool

---

#### Task 1.4: UserManager Core (Phase 1)
**Status**: Not Started  
**File**: `backend/utils/user_manager.py`  
**Scope**: ~200 lines  
**Dependencies**: Task 1.2, 1.3  
**Description**: User registration and profile management (persistent)  
**Deliverables**:
- UserManager class with:
  - load_all_users() - Load from users.json on init
  - user_exists(email) → bool
  - register_user(email, username) → user_dict
  - get_user(email) → user_dict
  - save_users() - Persist to users.json
  - Uses ColorPalette for color assignment

---

#### Task 1.5: RoomManager Core (Phase 1)
**Status**: Not Started  
**File**: `backend/utils/room_manager.py`  
**Scope**: ~250 lines  
**Dependencies**: Task 1.3, 1.4  
**Description**: Room creation, loading, and configuration persistence  
**Deliverables**:
- RoomManager class with:
  - load_all_rooms() - Load from rooms.json on init
  - generate_room_id() → str (format: room-{8chars})
  - create_room(name, config, creator_email) → room_id
  - load_room(room_id) → room_dict
  - save_room(room_id, config) → bool
  - get_room_state(room_id) → state_dict (or empty dict if inactive)
  - Validation using Validators

---

#### Task 1.6: App Setup & Structure
**Status**: Not Started  
**File**: `backend/app.py`  
**Scope**: ~100 lines (core only)  
**Dependencies**: Task 1.4, 1.5  
**Description**: aiohttp app initialization, managers setup, basic structure  
**Deliverables**:
- aiohttp Application setup
- Global room_manager and user_manager instances
- Environment variable loading
- Logging setup
- Static file serving for frontend
- Placeholder route definitions (no implementation yet)

---

#### Task 1.7: REST - Register/Get User Endpoints
**Status**: Not Started  
**File**: `backend/routes/users.py`  
**Scope**: ~150 lines  
**Dependencies**: Task 1.4, 1.6  
**Description**: REST endpoints for user management  
**Deliverables**:
- POST /api/user - Register or get existing user
- GET /api/user/{email} - Get user profile
- PUT /api/user/{email} - Update username
- Error handling with proper HTTP codes
- JSON request/response validation

---

#### Task 1.8: REST - Room Endpoints (Create & Load)
**Status**: Not Started  
**File**: `backend/routes/rooms.py`  
**Scope**: ~180 lines  
**Dependencies**: Task 1.5, 1.6  
**Description**: REST endpoints for room creation and retrieval  
**Deliverables**:
- POST /api/room - Create new room
- GET /api/room/{room_id} - Load room config and state
- GET /api/rooms - List active rooms (admin)
- Validation using Validators
- JSON responses with room state

---

### Frontend - Lander Page

#### Task 1.9: HTML - Landing & Registration
**Status**: Not Started  
**File**: `frontend/index.html`  
**Scope**: ~200 lines  
**Dependencies**: None  
**Description**: HTML structure for landing page and modals  
**Deliverables**:
- Semantic HTML5 structure
- Landing page with welcome message
- Registration modal with email/username inputs
- Room creation modal with name + grid editor (25 inputs)
- Room join modal with room ID input
- Connection status indicator
- Responsive layout (mobile-first)

---

#### Task 1.10: CSS - Styling & Themes
**Status**: Not Started  
**File**: `frontend/css/styles.css`  
**Scope**: ~300 lines  
**Dependencies**: None  
**Description**: Responsive CSS with color themes and layout  
**Deliverables**:
- CSS variables for colors, spacing, fonts
- Landing page styling
- Modal styling and animations
- Responsive grid layout (5x5)
- Form styling and validation indicators
- Touch-friendly button sizes (48px minimum)
- Dark/light theme support (optional)

---

#### Task 1.11: JavaScript - State Management
**Status**: Not Started  
**File**: `frontend/js/state.js`  
**Scope**: ~120 lines  
**Dependencies**: None  
**Description**: Client-side state store and helper functions  
**Deliverables**:
- appState object with:
  - currentUser (or null)
  - currentRoom (or null)
  - isConnected flag
- setState() function
- getState() function
- Reset functions for page transitions
- localStorage sync for user profile

---

#### Task 1.12: JavaScript - Room Creation Logic
**Status**: Not Started  
**File**: `frontend/js/room-creation.js`  
**Scope**: ~200 lines  
**Dependencies**: Task 1.11  
**Description**: Form handling for room creation  
**Deliverables**:
- Open/close room creation modal
- Grid editor: 25 inputs with validation
- Center cell locked to "FREE"
- Form submission handler
- API call to POST /api/room
- Error handling and user feedback
- Success: navigate to room join or direct join

---

#### Task 1.13: JavaScript - WebSocket Setup
**Status**: Not Started  
**File**: `frontend/js/websocket.js`  
**Scope**: ~150 lines  
**Dependencies**: Task 1.11  
**Description**: WebSocket client setup (no message handling yet)  
**Deliverables**:
- WebSocketClient class with:
  - connect() - Establish connection
  - disconnect() - Close connection
  - send(message) - Send JSON message
  - on(type, callback) - Register message handler
  - Auto-reconnect logic with exponential backoff
  - Connection status tracking
  - Error handling and logging

---

#### Task 1.14: JavaScript - Registration Logic
**Status**: Not Started  
**File**: `frontend/js/registration.js`  
**Scope**: ~150 lines  
**Dependencies**: Task 1.11, 1.13  
**Description**: User registration form handling  
**Deliverables**:
- Open/close registration modal
- Form validation (email, username)
- API call to POST /api/user
- Save user to localStorage
- Update appState.currentUser
- Show assigned color
- Transition to room selection screen

---

#### Task 1.15: JavaScript - Main App Orchestrator
**Status**: Not Started  
**File**: `frontend/js/app.js`  
**Scope**: ~180 lines  
**Dependencies**: Task 1.11, 1.12, 1.13, 1.14  
**Description**: Main app logic, page flow, event wiring  
**Deliverables**:
- Initialize app on page load
- Check localStorage for existing user
- Show registration or room selection
- Route between pages (landing → room creation → room join → game)
- Event listeners for all buttons
- Modal management
- Error display and handling

---

### Integration & Testing

#### Task 1.16: Backend Testing - Managers
**Status**: Not Started  
**File**: `backend/tests/test_managers.py`  
**Scope**: ~300 lines  
**Dependencies**: Task 1.4, 1.5  
**Description**: Unit tests for UserManager and RoomManager  
**Deliverables**:
- Test user registration
- Test user retrieval
- Test room creation
- Test room loading
- Test room persistence
- Test color assignment
- Test validation

---

#### Task 1.17: Manual Testing - Room Creation Flow
**Status**: Not Started  
**Scope**: Testing protocol  
**Dependencies**: All Phase 1 tasks  
**Description**: End-to-end testing of room creation  
**Deliverables**:
- User registration via browser
- Room creation via form
- Verify users.json updated
- Verify rooms.json updated
- Verify color assigned
- Verify room config persisted
- Test error cases (invalid inputs, existing emails)

---

## Phase 2: Room Join & Bingo Selection

### Backend

#### Task 2.1: RoomManager - Session State (Phase 2)
**Status**: Waiting for Phase 1  
**File**: `backend/utils/room_manager.py` (extend)  
**Scope**: ~200 lines  
**Dependencies**: Task 1.5  
**Description**: Add in-memory session state management  
**Deliverables**:
- add_user_to_room(room_id, user)
- remove_user_from_room(room_id, email)
- get_active_users(room_id)
- mark_bingo_cell(room_id, email, cell, selected)
- In-memory state per room
- Cleanup empty rooms

---

#### Task 2.2: WebSocket Handler
**Status**: Waiting for Phase 1  
**File**: `backend/routes/websocket.py`  
**Scope**: ~250 lines  
**Dependencies**: Task 1.6, 2.1  
**Description**: WebSocket connection and message routing  
**Deliverables**:
- Handle WS connections
- Route messages by type
- Broadcast to room clients
- Connection/disconnection handling
- Error handling and logging

---

#### Task 2.3: WebSocket Messages - Join & Bingo
**Status**: Waiting for Phase 1  
**File**: `backend/handlers/ws_messages.py`  
**Scope**: ~200 lines  
**Dependencies**: Task 2.2, 2.1  
**Description**: WebSocket message handlers  
**Deliverables**:
- join message handler
- bingo_select message handler
- room_state broadcast handler
- user_joined broadcast handler
- bingo_updated broadcast handler

---

### Frontend

#### Task 2.4: JavaScript - Room Join Logic
**Status**: Waiting for Phase 1  
**File**: `frontend/js/room-join.js`  
**Scope**: ~150 lines  
**Dependencies**: Task 1.11, 1.13  
**Description**: Room join form and WebSocket connection  
**Deliverables**:
- Open/close room join modal
- Room ID validation and entry
- URL parameter parsing (?room=room-id)
- Join via API call
- Connect WebSocket on successful join
- Send join message
- Error handling (room not found, full, etc.)

---

#### Task 2.5: HTML - Game Board (Bingo Grid)
**Status**: Waiting for Phase 1  
**File**: `frontend/index.html` (extend)  
**Scope**: ~100 lines (new section)  
**Dependencies**: None  
**Description**: Add game board HTML structure  
**Deliverables**:
- 5x5 bingo grid as div grid
- Clickable cells with text from config
- Colored circle indicators
- User list sidebar
- Reveal/Reset buttons
- Room info display

---

#### Task 2.6: CSS - Game Board Styling
**Status**: Waiting for Phase 1  
**File**: `frontend/css/styles.css` (extend)  
**Scope**: ~150 lines (new)  
**Dependencies**: None  
**Description**: Styling for game board  
**Deliverables**:
- Bingo grid layout and styling
- Cell hover effects
- Color circle styling
- User list styling
- Button styling for Reveal/Reset
- Responsive grid scaling

---

#### Task 2.7: JavaScript - Bingo UI & Interactions
**Status**: Waiting for Phase 1  
**File**: `frontend/js/bingo.js`  
**Scope**: ~200 lines  
**Dependencies**: Task 1.11, 2.1  
**Description**: Bingo grid rendering and click handling  
**Deliverables**:
- renderBingoGrid(config, selections)
- handleCellClick(cellIndex)
- renderColorCircles(selections)
- Send bingo_select message to server
- Update UI on bingo_updated message
- Prevent clicks when revealed

---

#### Task 2.8: JavaScript - UI Updates
**Status**: Waiting for Phase 1  
**File**: `frontend/js/ui.js`  
**Scope**: ~180 lines  
**Dependencies**: Task 1.11  
**Description**: General UI rendering functions  
**Deliverables**:
- renderUserList(users)
- updateConnectionStatus(connected)
- showNotification(message, type)
- showError(message)
- resetGameBoard()
- updateRoomInfo(room)

---

## Phase 3: Poker Selection & Reveal

### Backend

#### Task 3.1: WebSocket Messages - Poker & Reveal
**Status**: Waiting for Phase 2  
**File**: `backend/handlers/ws_messages.py` (extend)  
**Scope**: ~150 lines  
**Dependencies**: Task 2.3  
**Description**: Poker selection, reveal, and reset handlers  
**Deliverables**:
- poker_select message handler
- reveal message handler
- reset message handler
- Corresponding broadcast handlers

---

### Frontend

#### Task 3.2: HTML - Poker Selector
**Status**: Waiting for Phase 2  
**File**: `frontend/index.html` (extend)  
**Scope**: ~50 lines  
**Dependencies**: None  
**Description**: Add poker value selector  
**Deliverables**:
- 9 buttons for poker values: 0, 1, 2, 3, 5, 8, 13, 21, Split
- Selected state styling
- Vote counter display

---

#### Task 3.3: CSS - Poker Selector Styling
**Status**: Waiting for Phase 2  
**File**: `frontend/css/styles.css` (extend)  
**Scope**: ~80 lines  
**Dependencies**: None  
**Description**: Style poker selector  
**Deliverables**:
- Card/button layout (horizontal or wrap)
- Selected state styling
- Hover effects
- Vote counter styling

---

#### Task 3.4: JavaScript - Poker Selector
**Status**: Waiting for Phase 2  
**File**: `frontend/js/poker.js`  
**Scope**: ~150 lines  
**Dependencies**: Task 1.11, 2.7  
**Description**: Poker value selection logic  
**Deliverables**:
- renderPokerSelector(current_value)
- handlePokerClick(value)
- Send poker_select message
- Show vote status before reveal
- Disable after reveal
- renderPokerResults(selections)

---

#### Task 3.5: JavaScript - Reveal & Reset
**Status**: Waiting for Phase 2  
**File**: `frontend/js/game-controls.js`  
**Scope**: ~120 lines  
**Dependencies**: Task 2.7, 3.4  
**Description**: Reveal and Reset button logic  
**Deliverables**:
- handleRevealClick()
- handleResetClick()
- Send reveal/reset messages
- Enable/disable button states
- Show/hide selections appropriately
- Trigger UI updates

---

## Implementation Notes

### Code Organization Principles
- **One responsibility per file** - Each file handles one feature
- **Maximum ~300 lines per file** - Keep for readability
- **Modular imports** - Files can be understood independently
- **Minimal dependencies** - Reduce coupling between modules
- **Clear naming** - File name reflects content (e.g., `room-creation.js`)

### Testing Strategy
- Unit test each manager independently
- Test API endpoints with pytest
- Manual end-to-end testing per phase
- Test error cases and edge cases

### Deployment Order
1. Complete Phase 1 (room creation flow)
2. Deploy and verify
3. Complete Phase 2 (room join + bingo)
4. Deploy and verify
5. Complete Phase 3 (poker + reveal)
6. Final deployment

### File Size Guidelines
- **Utilities** (Validators, ColorPalette): 100-200 lines
- **Managers** (UserManager, RoomManager): 200-300 lines
- **Routes/Handlers**: 150-250 lines
- **Frontend Components** (UI, Bingo, Poker): 150-250 lines
- **Tests**: 200-400 lines (generous for comprehensive testing)

---

*Last Updated: 2026-08-12*
