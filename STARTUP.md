# BingoPoker - Startup Guide

## Quick Start (Shared Hosting)

### Step 1: Connect via SSH

```bash
ssh uid1124393@shellserver
cd ~/srvtech.hu/sub/bingopoker
```

### Step 2: Verify Python & Dependencies

```bash
# Check Python version (should be 3.8+)
python3 --version

# Install dependencies (one time only)
cd backend
pip3 install -r requirements.txt
cd ..
```

### Step 3: Launch the App

```bash
# Navigate to backend directory
cd backend

# Start the app (runs in foreground)
python3 app.py
```

You should see:
```
🚀 Starting BingoPoker on 0.0.0.0:8081
✓ Loaded 0 users
✓ Loaded 0 room configurations
```

### Step 4: Test the App (in another terminal)

```bash
# Health check
curl http://localhost:8081/health

# Register a user
curl -X POST http://localhost:8081/api/user \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "username": "TestUser"}'
```

### Step 5: Keep Running

The app runs in the foreground. To keep it running after disconnect, use one of:

#### Option A: tmux (recommended)
```bash
# Start a new session
tmux new-session -d -s bingopoker "cd ~/srvtech.hu/sub/bingopoker/backend && python3 app.py"

# Check if running
tmux list-sessions

# Reconnect to session
tmux attach-session -t bingopoker

# Detach: Ctrl+B then D
```

#### Option B: nohup
```bash
cd backend
nohup python3 app.py > app.log 2>&1 &
echo $! > app.pid  # Save PID

# View logs
tail -f app.log

# Stop the app
kill $(cat app.pid)
```

#### Option C: Run in background (simple)
```bash
cd backend
python3 app.py &  # Start in background
jobs  # List background jobs

# Bring to foreground if needed
fg

# Stop
kill %1  # Kill job 1
```

## File Structure

```
bingopoker/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── data/
│   │   ├── users.json
│   │   └── rooms.json
│   ├── utils/
│   │   ├── user_manager.py
│   │   ├── room_manager.py
│   │   ├── color_palette.py
│   │   └── validators.py
│   ├── routes/
│   │   ├── users.py
│   │   ├── rooms.py
│   │   └── debug.py
│   └── handlers/
│       └── websocket.py
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   ├── js/
│   │   ├── app.js
│   │   └── api.js
│   └── templates/
│       └── agile-default.json
├── .env
└── STARTUP.md
```

## Configuration

Edit `.env` in the project root:

```bash
HOST=0.0.0.0
PORT=8081
DEBUG=False
DATA_DIR=data  # relative to backend/app.py; defaults to backend/data/ if unset
```

## Troubleshooting

**App won't start: "Module not found"**
```bash
cd backend
pip3 install -r requirements.txt
```

**Port already in use**
```bash
# Find process using port 8081
lsof -i :8081

# Kill it
kill <PID>
```

**Connection refused**
- Make sure app is running
- Check with: `curl http://localhost:8081/health`
- If local: might need to use `curl http://127.0.0.1:8081/health`

**Want to stop the app**
```bash
# If in foreground: Ctrl+C
# If in background: kill %1  (or kill $(cat app.pid))
```

## Next Steps

Once app is running:
1. Test API endpoints (see DEVELOPMENT.md)
2. Implement room routes (Task 1.8)
3. Build frontend (Tasks 1.9-1.15)
4. Add WebSocket support
5. Deploy to production

For detailed development info: see [DEVELOPMENT.md](DEVELOPMENT.md)
