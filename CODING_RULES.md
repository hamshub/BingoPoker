# BingoPoker Development Coding Rules & Standards

## Overview
These rules guide all code generation by Copilot with user oversight. User only codes when necessary.

> **Note**: The file structures below reflect the original planning targets. The actual project consolidated further — the WebSocket handler lives at `backend/handlers/websocket.py` (not `routes/websocket.py` + `handlers/ws_messages.py`), and the frontend uses just two JS files (`js/app.js`, `js/api.js`) instead of the ten-file split shown here. See [README.md](README.md) for the current, accurate project structure.

---

## File Organization

### Principle: Separation of Concerns
- **One responsibility per file** - Each file has a single, clear purpose
- **Maximum file size: ~300 lines** - Improves readability and testability
- **Module naming reflects content** - File names clearly indicate what they contain

### Backend Structure
```
backend/
├── app.py                       # Main aiohttp app setup (100 lines)
├── requirements.txt             # Dependencies only
├── utils/
│   ├── __init__.py
│   ├── color_palette.py        # Color logic only (~100 lines)
│   ├── validators.py           # Validation functions only (~150 lines)
│   ├── user_manager.py         # User management only (~200 lines)
│   └── room_manager.py         # Room management only (~250 lines)
├── routes/
│   ├── __init__.py
│   ├── users.py                # User REST endpoints (~150 lines)
│   ├── rooms.py                # Room REST endpoints (~180 lines)
│   └── websocket.py            # WebSocket setup (~250 lines)
├── handlers/
│   ├── __init__.py
│   └── ws_messages.py          # WebSocket message handlers (~200+ lines)
└── data/
    ├── users.json              # Persistent user registry
    └── rooms.json              # Persistent room configs
```

### Frontend Structure
```
frontend/
├── index.html                   # Single HTML file (all layouts)
├── css/
│   └── styles.css              # All CSS (modular via classes)
└── js/
    ├── state.js                # State management (~120 lines)
    ├── websocket.js            # WebSocket client (~150 lines)
    ├── registration.js         # Registration flow (~150 lines)
    ├── room-creation.js        # Room creation flow (~200 lines)
    ├── room-join.js            # Room join flow (~150 lines)
    ├── bingo.js                # Bingo grid logic (~200 lines)
    ├── poker.js                # Poker selector logic (~150 lines)
    ├── game-controls.js        # Reveal/Reset logic (~120 lines)
    ├── ui.js                   # General UI helpers (~180 lines)
    └── app.js                  # Main orchestrator (~180 lines)
```

---

## Backend Code Standards

### Python Style
- **PEP 8 compliance** - Use black formatter for consistency
- **Type hints** - All function signatures include type hints
- **Docstrings** - Every class and function has a docstring
- **Async/await** - Use async functions for I/O (aiohttp handlers, file I/O)

### Class Structure
```python
class ClassName:
    """One-line description of class."""
    
    def __init__(self):
        """Initialize with docstring."""
        pass
    
    def public_method(self) -> ReturnType:
        """Docstring for public method."""
        pass
    
    def _private_method(self) -> ReturnType:
        """Docstring for private method."""
        pass
```

### Error Handling
- **All input validation** - Validate at entry points (routes)
- **Try/except sparingly** - Only catch specific exceptions
- **Return error objects** - Use (success: bool, data: any, error: str) tuple pattern
- **HTTP status codes** - Use appropriate codes (400, 404, 409, 500)

### Manager Classes
- **Single responsibility** - Each manager handles one resource
- **Persistence layer** - Managers handle read/write to JSON files
- **In-memory cache** - Load all data on init, keep sync'd
- **Public methods only** - No private "_internal" methods exposed in API

### Example Manager
```python
class UserManager:
    """Manages user profiles and persistence."""
    
    def __init__(self):
        """Load all users from file on startup."""
        self.users = {}
        self._load_from_file()
    
    def user_exists(self, email: str) -> bool:
        """Check if user already registered."""
        return email in self.users
    
    def register_user(self, email: str, username: str) -> dict:
        """Register new user or return existing."""
        if self.user_exists(email):
            return self.users[email]
        
        # Create new user
        color = ColorPalette.assign_color_new()
        user = {
            "email": email,
            "username": username,
            "color": color,
            "created_at": datetime.utcnow().isoformat()
        }
        self.users[email] = user
        self._save_to_file()
        return user
    
    def _load_from_file(self) -> None:
        """Load users from users.json."""
        pass
    
    def _save_to_file(self) -> None:
        """Save users to users.json."""
        pass
```

### Route Handlers
- **One route per function** - Don't combine multiple routes
- **Validation first** - Validate inputs immediately
- **Error responses** - Return JSON error objects
- **Consistent response format** - Use same JSON structure

### Example Route
```python
async def create_room(request: web.Request) -> web.Response:
    """POST /api/room - Create new room."""
    try:
        data = await request.json()
    except (json.JSONDecodeError, ValueError):
        return web.json_response(
            {"error": "invalid_json", "message": "Invalid JSON body"},
            status=400
        )
    
    # Validate inputs
    if not Validators.validate_room_name(data.get("name")):
        return web.json_response(
            {"error": "invalid_room_name", "message": "Name required, max 100 chars"},
            status=400
        )
    
    # Process
    room_id = room_manager.create_room(...)
    
    # Return success
    return web.json_response({
        "room_id": room_id,
        "status": "created"
    }, status=201)
```

---

## Frontend Code Standards

### JavaScript Style
- **Vanilla JS only** - No frameworks, vanilla DOM manipulation
- **ES6+ syntax** - Use const/let, arrow functions, template literals
- **Module pattern** - Each file exports single object/function
- **No global namespace pollution** - Use IIFE or module pattern

### File Structure
Each JS file should:
```javascript
/**
 * module-name.js - One sentence description
 */

// Constants
const CONSTANT_VALUE = "value";

// Private functions (prefix with _)
function _privateHelper() {
  // ...
}

// Exported public function/object
const ModuleName = {
  init() {
    // Initialize
  },
  
  publicMethod() {
    // Public method
  }
};
```

### State Management Pattern
```javascript
const appState = {
  currentUser: null,
  currentRoom: null,
  
  // Getters
  getCurrentUser() {
    return this.currentUser;
  },
  
  // Setters
  setCurrentUser(user) {
    this.currentUser = user;
    localStorage.setItem("bingopoker_user", JSON.stringify(user));
  },
  
  // Actions
  async registerUser(email, username) {
    const response = await fetch("/api/user", {
      method: "POST",
      body: JSON.stringify({ email, username })
    });
    
    if (!response.ok) {
      throw new Error("Registration failed");
    }
    
    const user = await response.json();
    this.setCurrentUser(user);
    return user;
  }
};
```

### Event Handling
- **Event delegation** - Use event delegation for dynamic elements
- **One handler per action** - Don't combine handlers
- **Clear naming** - Handler names start with "handle" or "on"

### Example Event Handler
```javascript
function handleBingoClick(event) {
  const cell = event.target.closest("[data-cell-index]");
  if (!cell) return;
  
  const cellIndex = parseInt(cell.dataset.cellIndex, 10);
  const isSelected = cell.classList.contains("selected");
  
  // Toggle selection
  if (isSelected) {
    cell.classList.remove("selected");
  } else {
    cell.classList.add("selected");
  }
  
  // Send to server
  WebSocketClient.send({
    type: "bingo_select",
    cell: cellIndex,
    selected: !isSelected
  });
}
```

### DOM Manipulation
- **Use data attributes** - Store values in `data-*` attributes
- **Class toggling** - Use classList for styling
- **Template literals** - Build HTML with backticks
- **Efficient updates** - Batch DOM updates, use DocumentFragment for lists

### Example DOM Update
```javascript
function renderUserList(users) {
  const container = document.getElementById("user-list");
  const fragment = document.createDocumentFragment();
  
  users.forEach(user => {
    const li = document.createElement("li");
    li.className = "user-item";
    li.style.borderColor = user.color;
    li.innerHTML = `
      <span class="color-indicator" style="background: ${user.color}"></span>
      <span class="username">${user.username}</span>
    `;
    fragment.appendChild(li);
  });
  
  container.innerHTML = ""; // Clear
  container.appendChild(fragment);
}
```

### CSS Naming
- **BEM convention** - Block__Element--Modifier
- **CSS variables** - Use :root variables for colors/spacing
- **Mobile-first** - Base styles for mobile, media queries for larger screens
- **Semantic classes** - Class names describe purpose, not appearance

### Example CSS
```css
:root {
  --color-primary: #FF6B6B;
  --color-text: #2f2a21;
  --spacing-unit: 8px;
  --border-radius: 8px;
}

.bingo-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--spacing-unit);
}

.bingo-cell {
  padding: var(--spacing-unit);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all 0.2s ease;
}

.bingo-cell:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.bingo-cell--selected {
  background: var(--color-primary);
  color: white;
}

@media (max-width: 768px) {
  .bingo-grid {
    gap: 4px;
  }
}
```

---

## API Design Standards

### REST Endpoints
- **Resource-oriented** - URLs represent resources, not actions
- **Standard methods** - GET (read), POST (create), PUT (update), DELETE (delete)
- **Consistent paths** - `/api/{resource}` or `/api/{resource}/{id}`
- **Status codes** - 200 (ok), 201 (created), 400 (bad request), 404 (not found), 500 (server error)

### JSON Response Format
```json
{
  "status": "success",
  "data": { /* actual data */ }
}
```

```json
{
  "status": "error",
  "error": "error_code",
  "message": "Human-readable message"
}
```

### WebSocket Messages
- **Type field required** - Every message must have `type` field
- **Room ID required** - Include `room_id` for routing
- **Timestamp optional** - Add for debugging/logging
- **Structured payload** - Consistent format for each message type

---

## Testing Standards

### Backend Tests (pytest)
- **One test per behavior** - Test single functionality per test
- **Descriptive names** - `test_create_room_with_valid_config_succeeds`
- **Arrange-Act-Assert** - Clear test structure
- **Fixtures for setup** - Use pytest fixtures for common setup

### Example Test
```python
@pytest.fixture
def room_manager():
    """Provide fresh RoomManager instance."""
    return RoomManager()

def test_create_room_with_valid_config_succeeds(room_manager):
    """Test that valid room creation works."""
    # Arrange
    config = {"grid": [[...], [...], ..., [...], [...]]}
    
    # Act
    room_id = room_manager.create_room("Test Room", config, "user@test.com")
    
    # Assert
    assert room_id is not None
    assert room_manager.load_room(room_id) is not None
    assert room_manager.load_room(room_id)["name"] == "Test Room"
```

### Frontend Testing
- **Manual end-to-end testing** - Test user flows in browser
- **Console checks** - Verify no errors in browser console
- **Network tab** - Verify correct API calls
- **WebSocket inspection** - Check message format and timing

---

## Documentation Standards

### Inline Comments
- **Explain WHY, not WHAT** - Code explains what, comments explain why
- **Sparingly used** - Don't over-comment obvious code
- **Complex logic only** - Comment tricky algorithms or business logic

### Function Docstrings
```python
def register_user(self, email: str, username: str) -> dict:
    """
    Register a new user or return existing user profile.
    
    Args:
        email: User email address (unique)
        username: User display name
    
    Returns:
        User dict with {email, username, color, created_at}
    
    Raises:
        ValueError: If email or username invalid
    """
    pass
```

### README Files
- **Keep documentation alongside code**
- **Update docs when code changes**
- **Link to relevant documentation**
- **Include examples**

---

## Version Control Standards

### Commit Messages
- **Clear and descriptive** - "Add bingo cell selection handler"
- **Present tense** - "Add" not "Added"
- **Reference task** - "Task 1.7: Implement bingo selection"
- **One logical change per commit**

### Branch Strategy
- **Main branch** - Always deployable, tested code
- **Feature branches** - One task per branch
- **Branch naming** - `task-1-7-bingo-selection`

---

## Performance Guidelines

### Backend
- **Lazy load** - Load room configs on-demand, not all at startup
- **Batch broadcasts** - Group related updates in single message
- **Room cleanup** - Remove empty rooms from memory after timeout
- **Limit broadcasts** - Only send to clients in specific room

### Frontend
- **Debounce events** - Debounce rapid cell clicks (100ms)
- **Cache DOM queries** - Store frequently accessed DOM nodes
- **Lazy render** - Only render visible elements
- **Minimize reflows** - Batch DOM changes

---

## Security Guidelines

### Input Validation
- **All inputs validated** - Never trust client input
- **Server-side validation** - Always validate on backend
- **Sanitize output** - Escape HTML in user-provided text
- **Length limits** - Enforce max lengths for all fields

### Data Protection
- **No sensitive data in localStorage** - Only non-sensitive user profile
- **HTTPS in production** - Always use secure WebSocket (WSS)
- **Rate limiting** - Limit requests per user (future enhancement)
- **No credentials in URLs** - Never pass auth info in query params

---

## Error Handling Standards

### Backend Errors
- **Validate first** - Check inputs before processing
- **Specific errors** - Return specific error codes (invalid_email, room_not_found, etc.)
- **Log errors** - Log all errors for debugging
- **Safe responses** - Never expose internal errors to client

### Frontend Errors
- **User-friendly messages** - Show helpful error messages
- **Error recovery** - Provide way to recover (retry, cancel, etc.)
- **Console logging** - Log to console for debugging
- **Toast/modal display** - Show errors prominently

---

## Dependency Management

### Backend Dependencies
- **Minimal** - Only essential libraries (aiohttp, pytest)
- **Well-maintained** - Choose active, popular libraries
- **Version pinning** - Pin versions in requirements.txt for reproducibility

### Frontend Dependencies
- **Zero external JS** - Use vanilla JavaScript only
- **Minimal CSS** - Write custom CSS, no CSS frameworks initially
- **No build step** - Should work without bundling/transpiling

---

## Deployment Checklist

Before deploying:
- [ ] All tests pass
- [ ] No console errors in browser
- [ ] API endpoints tested manually
- [ ] WebSocket messages verified
- [ ] JSON files properly persisted
- [ ] Error cases handled
- [ ] Performance acceptable (< 2s page load)
- [ ] Mobile responsive verified
- [ ] Documentation updated

---

## Review Checklist (User Oversight)

Before approving code:
- [ ] Follows this coding rules document
- [ ] File sizes reasonable (~300 lines max)
- [ ] Clear separation of concerns
- [ ] Proper error handling
- [ ] Tests included for critical paths
- [ ] Documentation clear and updated
- [ ] No unnecessary complexity
- [ ] Performance acceptable

---

*Last Updated: 2026-08-12*
