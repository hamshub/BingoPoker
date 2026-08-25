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
Starting BingoPoker on 0.0.0.0:8081
```

Application events are written to `backend/logs/bingopoker.log`; only warnings and errors are echoed to the console.

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
│   ├── requirements-dev.txt
│   ├── data/
│   │   ├── users.json
│   │   ├── rooms.json
│   │   └── .email_pepper       # auto-generated secret — back this up
│   ├── logs/
│   │   └── bingopoker.log
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

Edit `.env` in the project root (see `.env.example`):

```bash
HOST=0.0.0.0
PORT=8081
DEBUG=False              # True also exposes the destructive /api/debug endpoints
DATA_DIR=data            # relative to backend/app.py; defaults to backend/data/ if unset
EMAIL_HASH_PEPPER=       # leave empty to auto-generate backend/data/.email_pepper
```

### Email pepper

User emails are stored only as HMAC-SHA256 digests. The pepper used for that digest is read from
`EMAIL_HASH_PEPPER`, or generated once into `backend/data/.email_pepper`. **Back this file up and
keep it out of version control** — losing or changing it orphans every existing user record.

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

**Everyone has to log in again after a restart**
- Check that `backend/data/.email_pepper` still exists and was not regenerated.

## Production Checklist

1. `DEBUG=False` so the data-wiping `/api/debug` endpoints are not registered.
2. Back up `backend/data/` (including `.email_pepper`).
3. Serve behind HTTPS so WebSocket traffic upgrades to `wss://`.
4. Rotate or truncate `backend/logs/bingopoker.log` periodically — the app does not rotate it.

For detailed development info: see [DEVELOPMENT.md](DEVELOPMENT.md)
