# BingoPoker - Agile Scrum Poker with Bingo Cards

## Overview

BingoPoker is a collaborative web-based application designed for agile teams during sprint refinement sessions. It combines the power of planning poker (Fibonacci estimation) with an interactive 5x5 bingo card, allowing teams to visualize story points while identifying consensus and outliers in real-time.

## Features

### Core Features
- **Configurable Bingo Card**: 5x5 grid with custom text for each cell
- **Planning Poker**: Fibonacci scale (0, 1, 2, 3, 5, 8, 13, 21, Split)
- **Real-time Collaboration**: Multiple users can participate simultaneously
- **Color-coded Users**: Each user gets a unique color from a 10-color palette for easy identification
- **Persistent Rooms**: Room configurations are saved and remembered even after users leave
- **User Caching**: Users are recognized on return visits via email/username

### Session Features
- **Bingo Card Selection**: Users click on cells to mark their interest/allocation
- **Poker Selection**: Users choose their story point estimate
- **Reveal Mechanism**: Votes are hidden until explicitly revealed
- **Visual Feedback**: Colored circles show which user selected which bingo card and poker value
- **Reset Functionality**: Enables new estimation rounds without losing room configuration

### Technical Constraints
- Maximum 10 users per room (one per color)
- Selections are not persistent (lost when all users leave)
- Room configurations persist indefinitely
- 5x5 bingo card grid
- 9 poker values available

## Project Structure

```
BingoPoker/
├── README.md                 # This file
├── ARCHITECTURE.md           # System design and component overview
├── DATA_STRUCTURES.md        # JSON schemas and data formats
├── USER_FLOW.md             # Step-by-step user interaction flow
├── API_SPECIFICATIONS.md    # WebSocket and HTTP endpoints
├── DEVELOPMENT.md           # Setup and development guide
├── STARTUP.md               # Deployment and hosting guide
│
├── backend/
│   ├── app.py               # aiohttp app factory, routes, startup
│   ├── requirements.txt     # Production Python dependencies
│   ├── requirements-dev.txt # Dev/test dependencies
│   ├── utils/
│   │   ├── room_manager.py      # Room config persistence + session state
│   │   ├── user_manager.py      # User registration and persistence
│   │   ├── color_palette.py     # 10-color palette assignment
│   │   └── validators.py        # Input validation helpers
│   ├── routes/
│   │   ├── users.py             # POST/GET/PUT /api/user
│   │   ├── rooms.py             # POST/GET /api/room
│   │   └── debug.py             # DEV ONLY: delete endpoints
│   ├── handlers/
│   │   └── websocket.py         # WebSocket lifecycle and message handling
│   └── data/
│       ├── users.json           # User registry (email → username, role)
│       └── rooms.json           # Room configurations (roomId → config)
│
├── frontend/
│   ├── index.html           # Single-page app shell (3 screens)
│   ├── css/
│   │   └── styles.css       # Dark theme, Outfit font, responsive layout
│   ├── js/
│   │   ├── app.js           # All UI state, navigation, and WS handling
│   │   └── api.js           # REST API client + GridUtils constants
│   └── templates/
│       └── agile-default.json  # Importable default bingo grid template
│
└── tests/
    └── (unit tests — see DEVELOPMENT.md)
```

## Tech Stack

### Backend
- **Framework**: Python with aiohttp (for async WebSocket support)
- **Storage**: JSON files (local persistence)
- **Protocol**: WebSocket for real-time updates

### Frontend
- **Languages**: HTML5, CSS3, JavaScript (Vanilla)
- **Communication**: WebSocket client
- **Styling**: Responsive CSS with color themes

## Quick Start

See [STARTUP.md](STARTUP.md) for detailed startup instructions.

```bash
# Install dependencies (one time)
cd backend
pip3 install -r requirements.txt
cd ..

# Run the server
cd backend
python3 app.py

# Open browser
http://localhost:8081
```

## User Journey

1. **First Visit**: User prompted to enter email and username → assigned random color
2. **Join Room**: Enter or create room via unique URL
3. **Configure**: (Room creator) Set up 5x5 bingo card text
4. **Play Round**:
   - Users select bingo card cells
   - Users select poker value
   - One user clicks Reveal
   - All selections become visible with color coding
5. **Review**: Visual identification of consensus and outliers
6. **Reset**: Clear selections for next round (or create new room)

## Key Design Decisions

- **Real-time WebSocket**: For instant updates across all participants
- **Local JSON Storage**: Simple, serverless persistence without databases
- **Color-coded Visibility**: Users instantly recognize each other's selections
- **Persistent Rooms**: Enables re-using configurations across sessions
- **Hidden Votes Until Reveal**: Prevents anchoring bias in estimations
- **20-User Limit**: Matches available color palette and prevents performance issues

## File Documentation

- [STARTUP.md](STARTUP.md) - How to launch the app (shared hosting & local)
- [ARCHITECTURE.md](ARCHITECTURE.md) - System components and data flow
- [DATA_STRUCTURES.md](DATA_STRUCTURES.md) - JSON schemas and file formats
- [USER_FLOW.md](USER_FLOW.md) - Detailed interaction flows
- [API_SPECIFICATIONS.md](API_SPECIFICATIONS.md) - WebSocket messages and endpoints
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development setup and testing guide

## Next Steps

1. Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
2. Review [DATA_STRUCTURES.md](DATA_STRUCTURES.md) for storage format
3. Set up development environment using [DEVELOPMENT.md](DEVELOPMENT.md)
4. Begin implementation following the documented API specifications

---

*Last Updated: 2026-08-12*
