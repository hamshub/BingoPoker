# Development Guide - BingoPoker

## Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- A code editor (VS Code recommended)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Setup (5 minutes)

```bash
# 1. Navigate to project directory
cd /path/to/BingoPoker

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r backend/requirements.txt

# 5. Run the server
python backend/app.py

# 6. Open browser
# Navigate to http://localhost:8081
```

Server will output:
```
Python demo listening on http://0.0.0.0:8081
WebSocket endpoint: ws://0.0.0.0:8081/ws
```

---

## Project Structure

```
BingoPoker/
├── README.md                    # Project overview
├── ARCHITECTURE.md              # System design
├── DATA_STRUCTURES.md           # JSON schemas
├── USER_FLOW.md                 # User interactions
├── API_SPECIFICATIONS.md        # REST and WebSocket API
├── DEVELOPMENT.md               # This file
│
├── backend/
│   ├── app.py                   # Main application entry point
│   ├── requirements.txt         # Python dependencies
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── room_manager.py      # Room logic and state
│   │   ├── user_manager.py      # User registration and caching
│   │   ├── color_palette.py     # Color assignment logic
│   │   └── validators.py        # Input validation
│   └── data/
│       ├── users.json           # User registry (persistent)
│       └── rooms.json           # Room configs (persistent)
│
├── frontend/
│   ├── index.html               # Main HTML (embedded in app.py)
│   ├── css/
│   │   └── styles.css           # Application styles
│   └── js/
│       ├── app.js               # All UI state, navigation, WS handling
│       └── api.js               # REST API client + GridUtils constants
│
└── tests/
    ├── __init__.py
    ├── test_room_manager.py     # Room tests
    ├── test_user_manager.py     # User tests
    └── test_api.py              # API endpoint tests
```

---

## Dependencies

### Backend (`requirements.txt` / `requirements-dev.txt`)

**Production** (`requirements.txt`):
```
aiohttp>=3.9.0
aiofiles>=23.2.0
python-dotenv>=1.0.0
```

**Dev/test** (`requirements-dev.txt`):
```
pytest>=7.4.3
pytest-aiohttp>=1.3.0
```

**Purpose of each**:
- `aiohttp`: Async web framework with native WebSocket support
- `aiofiles`: Async file I/O for JSON persistence
- `python-dotenv`: Load environment variables from `.env`
- `pytest` / `pytest-aiohttp`: Test framework with async support

### Frontend
Pure HTML5, CSS3, and JavaScript — no build step, no framework, no npm.

---

## Configuration

### Environment Variables

Create `.env` file in project root:

```env
HOST=0.0.0.0
PORT=8081
DEBUG=True
DATA_DIR=data  # relative to backend/app.py; omit to use default (backend/data/)
```

### Default Values

If `.env` not found, or `DATA_DIR` not set:
```python
HOST = "0.0.0.0"
PORT = 8081
DEBUG = False
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")  # always relative to app.py
```

> **Note**: Relative `DATA_DIR` values are resolved against `app.py`'s directory, not the working directory.

---

## Backend Development

### Main Application (`backend/app.py`)

**Structure**:
```python
import json
import os
from aiohttp import web
from utils.room_manager import RoomManager
from utils.user_manager import UserManager

# Global managers
room_manager = RoomManager()
user_manager = UserManager()

# HTTP Handlers
async def index(request: web.Request) -> web.Response:
    # Serve HTML
    pass

async def health(request: web.Request) -> web.Response:
    # Health check
    pass

async def register_user(request: web.Request) -> web.Response:
    # POST /api/user
    pass

async def get_user(request: web.Request) -> web.Response:
    # GET /api/user/{email}
    pass

async def update_user(request: web.Request) -> web.Response:
    # PUT /api/user/{email}
    pass

async def create_room(request: web.Request) -> web.Response:
    # POST /api/room
    pass

async def get_room(request: web.Request) -> web.Response:
    # GET /api/room/{room_id}
    pass

async def list_rooms(request: web.Request) -> web.Response:
    # GET /api/rooms (optional admin)
    pass

# WebSocket Handler
async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    # Handle WS connections and messages
    pass

# Application Factory
def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/health", health)
    app.router.add_post("/api/user", register_user)
    app.router.add_get("/api/user/{email}", get_user)
    app.router.add_put("/api/user/{email}", update_user)
    app.router.add_post("/api/room", create_room)
    app.router.add_get("/api/room/{room_id}", get_room)
    app.router.add_get("/api/rooms", list_rooms)
    app.router.add_get("/ws", websocket_handler)
    return app

if __name__ == "__main__":
    web.run_app(create_app(), host=HOST, port=PORT)
```

### Room Manager (`backend/utils/room_manager.py`)

Manages room state and persistence.

**Key Methods**:
```python
class RoomManager:
    def __init__(self):
        self.rooms = {}  # In-memory active rooms
        self.load_all_rooms()
    
    def load_all_rooms(self):
        # Load persisted rooms from rooms.json
        pass
    
    def create_room(self, name, config, creator_email):
        # Create new room
        # Returns: room_id
        pass
    
    def load_room(self, room_id):
        # Load room config from file
        pass
    
    def save_room(self, room_id, config):
        # Persist room to rooms.json
        pass
    
    def get_room_state(self, room_id):
        # Get current in-memory state
        pass
    
    def add_user(self, room_id, user):
        # Add user to room session
        pass
    
    def remove_user(self, room_id, email):
        # Remove user from room session
        pass
    
    def mark_bingo_cell(self, room_id, email, cell, selected):
        # Update bingo selection
        pass
    
    def set_poker_value(self, room_id, email, value):
        # Update poker selection
        pass
    
    def reveal_room(self, room_id):
        # Reveal all selections
        pass
    
    def reset_room(self, room_id):
        # Clear selections for new round
        pass
    
    def cleanup_empty_room(self, room_id):
        # Remove room from memory if empty
        pass
```

### User Manager (`backend/utils/user_manager.py`)

Manages user profiles and color assignments.

**Key Methods**:
```python
class UserManager:
    def __init__(self):
        self.users = {}  # Cached users
        self.load_all_users()
    
    def load_all_users(self):
        # Load from users.json
        pass
    
    def user_exists(self, email):
        # Check if user registered
        pass
    
    def register_user(self, email, username):
        # Create new user with color
        # Returns: user object
        pass
    
    def get_user(self, email):
        # Get user by email
        pass
    
    def update_user(self, email, username):
        # Update username
        pass
    
    def save_users(self):
        # Persist users to users.json
        pass
```

### Color Palette (`backend/utils/color_palette.py`)

```python
class ColorPalette:
    COLORS = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A",
        "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E2",
        "#F8B195", "#C7CEEA", "#FF85B3", "#64DDAA",
        "#FFD23F", "#3D5A80", "#C1666B", "#48A9A6",
        "#E4C1F9", "#F4A261", "#2A9D8F", "#E76F51"
    ]
    
    @staticmethod
    def assign_color(room_id, used_colors):
        # Get next available color for room
        pass
    
    @staticmethod
    def get_color_by_index(index):
        # Get color by palette index
        pass
```

### Validators (`backend/utils/validators.py`)

```python
class Validators:
    @staticmethod
    def validate_email(email: str) -> bool:
        pass
    
    @staticmethod
    def validate_username(username: str) -> bool:
        pass
    
    @staticmethod
    def validate_room_name(name: str) -> bool:
        pass
    
    @staticmethod
    def validate_grid(grid: list) -> bool:
        # Check 5x5, center is "FREE"
        pass
    
    @staticmethod
    def validate_cell_text(text: str) -> bool:
        pass
    
    @staticmethod
    def validate_cell_index(cell: int) -> bool:
        pass
    
    @staticmethod
    def validate_poker_value(value: str) -> bool:
        pass
```

---

## Frontend Development

### HTML Structure (`frontend/index.html`)

Should include:
- User registration form (modal)
- Room selection screen
- Room view with:
  - Bingo card grid (5×5)
  - User list panel
  - Poker selector (9 buttons)
  - Reveal/Reset buttons
  - Connection status indicator

### CSS Styling (`frontend/css/styles.css`)

Use CSS variables for theming:
```css
:root {
  --primary: #FF6B6B;
  --secondary: #4ECDC4;
  --bg: #f9f7f1;
  --panel: #fffefa;
  --ink: #2f2a21;
}
```

### JavaScript Modules

**`js/state.js`** - Client state:
```javascript
const appState = {
  currentUser: null,
  currentRoom: null,
  roomState: {
    bingo: {},
    poker: {},
    revealed: false
  },
  isConnected: false
};
```

**`js/websocket.js`** - Connection:
```javascript
class WebSocketClient {
  constructor(url) { }
  connect() { }
  disconnect() { }
  send(message) { }
  on(type, callback) { }
  reconnect() { }
}
```

**`js/ui.js`** - Rendering:
```javascript
function renderBingoGrid(config, selections) { }
function renderPokerSelector(selections) { }
function renderUserList(users) { }
function updateConnectionStatus(connected) { }
```

**`js/app.js`** - Main logic:
```javascript
class BingoPokerApp {
  constructor() { }
  initialize() { }
  handleBingoClick(cell) { }
  handlePokerSelect(value) { }
  handleReveal() { }
  handleReset() { }
}
```

---

## Testing

### Run Tests

```bash
pytest tests/

# With verbose output
pytest tests/ -v

# Specific test file
pytest tests/test_room_manager.py

# With coverage
pytest tests/ --cov=backend --cov-report=html
```

### Test Structure

**`tests/test_room_manager.py`**:
```python
import pytest
from backend.utils.room_manager import RoomManager

@pytest.fixture
def room_manager():
    return RoomManager()

def test_create_room(room_manager):
    room_id = room_manager.create_room("Test", config, "user@test.com")
    assert room_id is not None
    assert room_manager.load_room(room_id) is not None

def test_mark_bingo_cell(room_manager):
    # Test bingo selection
    pass

def test_reveal_room(room_manager):
    # Test reveal functionality
    pass
```

---

## Debugging

### Debug Logging

Add to `backend/app.py`:
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# In handlers:
logger.debug(f"Room joined: {room_id}")
logger.info(f"User registered: {email}")
logger.error(f"Error processing message: {error}")
```

### Browser DevTools

**Chrome/Edge/Firefox**:
1. Press F12 to open DevTools
2. Console tab: JavaScript errors/logs
3. Network tab: HTTP requests and WebSocket frames
4. Application tab: localStorage inspection

### WebSocket Inspection

**View WebSocket messages** in Network tab:
1. Open DevTools → Network tab
2. Look for "ws" entries
3. Click WebSocket connection
4. Messages sub-tab shows sent/received

### File Watching (Optional)

Install `watchdog` for auto-reload:
```bash
pip install watchdog
```

Then use in development:
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Auto-reload on file change
```

---

## Performance Optimization

### Backend

1. **Connection Pooling**: Reuse WebSocket connections
2. **Lazy Loading**: Load room configs on-demand
3. **Memory Management**: Clean up empty rooms
4. **Broadcast Optimization**: Only send to clients in specific room

### Frontend

1. **Debounce**: Debounce rapid bingo selections
2. **Caching**: Cache room config locally
3. **Lazy Rendering**: Only render visible elements
4. **Bundle Minification**: Minify JS/CSS (optional)

---

## Deployment Preparation

### Environment Setup

**Production `.env`**:
```env
HOST=0.0.0.0
PORT=8081
DEBUG=False
DATA_DIR=/data/bingopoker
```

### Data Backup

```bash
# Backup user and room data
cp -r backend/data backend/data.backup.$(date +%Y%m%d)
```

### Running in Production

Option 1: **Gunicorn with Uvicorn**:
```bash
pip install gunicorn uvicorn
uvicorn backend.app:app --host 0.0.0.0 --port 8081 --workers 4
```

Option 2: **Docker** (future):
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["python", "app.py"]
```

---

## Common Issues & Solutions

### Issue: Port Already in Use
```bash
# Find process using port 8081
lsof -i :8081  # macOS/Linux

# Kill process
kill -9 <PID>

# Or use different port
PORT=8082 python backend/app.py
```

### Issue: WebSocket Connection Failed
- Check browser console for errors
- Verify WebSocket URL format (ws:// or wss://)
- Check server is running
- Check firewall settings

### Issue: Data Not Persisting
- Verify `backend/data/` directory exists
- Check file permissions (readable/writable)
- Verify JSON file syntax is valid
- Clear browser localStorage if needed

### Issue: Users See Each Other's Hidden Selections
- Verify `revealed` flag properly managed
- Check poker values only sent after reveal
- Check WebSocket message filtering

---

## Best Practices

### Code Style
- Use PEP 8 for Python
- Use Prettier for JavaScript/HTML
- Add type hints to Python functions
- Add docstrings to all functions

### Security
- Validate all inputs (server-side)
- Sanitize user-provided text
- Use HTTPS/WSS in production
- Implement rate limiting
- No sensitive data in localStorage

### Performance
- Minimize WebSocket message size
- Batch updates when possible
- Clean up event listeners
- Test with 20 concurrent users

### Testing
- Unit test all managers
- Test API endpoints
- Test WebSocket flow end-to-end
- Test error cases

---

## Useful Commands

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run server
python backend/app.py

# Run tests
pytest tests/

# Format Python code
black backend/

# Lint Python code
flake8 backend/

# Run with auto-reload (development)
python -m pip install watchdog
python -m watchdog backend/app.py

# Create virtual environment
python -m venv venv

# Activate venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate      # Windows
```

---

## Next Steps

1. **Set up development environment** (follow Quick Start)
2. **Review architecture** (read ARCHITECTURE.md)
3. **Implement Room Manager** (backend/utils/room_manager.py)
4. **Implement User Manager** (backend/utils/user_manager.py)
5. **Implement HTTP endpoints** (backend/app.py)
6. **Implement WebSocket handler** (backend/app.py)
7. **Build frontend HTML/CSS** (frontend/)
8. **Build frontend JavaScript** (frontend/js/)
9. **Write tests** (tests/)
10. **Deploy to production**

---

## Getting Help

- Review relevant documentation files (README, ARCHITECTURE, etc.)
- Check error messages in console/DevTools
- Add logging for debugging
- Test endpoints with curl/Postman
- Use browser DevTools for frontend debugging

---

*Last Updated: 2026-08-12*
