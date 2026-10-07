# BingoPoker - Startup Guide

## Quick Start (Shared Hosting)

### Step 1: Connect via SSH

```bash
ssh <user>@<host>
cd ~/<path-to>/bingopoker
```

### Step 2: Verify Python & Dependencies

```bash
# Check Python version (should be 3.9+)
python3 --version

# Install dependencies (one time only, from the project root)
pip3 install -r requirements.txt
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

Application events are written to `backend/logs/bingopoker.log` (or `LOG_DIR`), rotated at midnight with 30 files kept; only warnings and errors are echoed to the console.

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
tmux new-session -d -s bingopoker "cd ~/<path-to>/bingopoker/backend && python3 app.py"

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

## Docker Deployment (NAS)

Every push to `main` runs `.github/workflows/docker.yml`. Its `test` job runs `pytest`; only
if that passes does `build-and-publish` build the image and push
`ghcr.io/<github-owner>/bingopoker:latest` (plus a `:<commit sha>` tag), where `<github-owner>` is
the repository owner in lowercase. The build passes the commit
SHA and build time as `APP_VERSION` / `BUILD_DATE`, which the app shows as
"Version <sha> · <date>" at the bottom of the room list info block (and returns from
`/api/version`).

`docker-compose.yml` runs three containers:

| Container | Purpose |
| --- | --- |
| `bingopoker` | The app, on host port `40550`; data in `/share/Container/bingopoker/data` |
| `bingopoker-caddy` | HTTPS reverse proxy on host ports `4080`/`4443`, using `/share/Container/bingopoker/Caddyfile` |
| `bingopoker-watchtower` | Checks ghcr.io every 5 minutes and recreates `bingopoker` when a new `latest` image is published |

Watchtower only updates containers labelled `com.centurylinklabs.watchtower.enable=true`
(currently just `bingopoker`). It pulls anonymously, so the ghcr.io package must be public.

The NAS keeps its own copy of the compose file; after changing `docker-compose.yml` in the
repo, copy it to the NAS and apply it from that directory:

```bash
docker compose pull
docker compose up -d
```

`docker restart bingopoker` does **not** pick up a new image — the container must be
recreated (`docker compose up -d`). Check update activity with
`docker logs bingopoker-watchtower --tail 20`. Recreating the container (by Watchtower or by
hand) wipes in-progress rounds, since session state is in memory only.

### Logs

The image sets `LOG_DIR=/app/data/logs`, so logs live in the data volume
(`/share/Container/bingopoker/data/logs` on the NAS) and survive container updates.
`bingopoker.log` is today's file; older days are `bingopoker.log.YYYY-MM-DD`, and 30 files are
kept.

### Admin pages (`/logs`, `/analytics`)

The log viewer and usage statistics are enabled by `ADMIN_PASSWORD`. Settings live in a `.env`
file next to `docker-compose.yml` on the NAS (never commit it). The compose file loads it with
`env_file`, so every variable in it is passed into the `bingopoker` container:

```bash
# .env (next to docker-compose.yml) — see the Docker section of .env.example
BINGOPOKER_IMAGE=ghcr.io/<github-owner>/bingopoker:latest
ADMIN_PASSWORD=<password>
```

`BINGOPOKER_IMAGE` is required; `docker compose` refuses to start without it. `HOST`, `PORT`,
`DEBUG`, `DATA_DIR` and `LOG_DIR` are fixed in `docker-compose.yml` and win over `.env`. Write a
literal `$` in a value as `$$`, since compose treats `$` as a variable reference.

Apply changes with `docker compose up -d`. Later settings changes only need a `.env` edit plus
`docker compose up -d`; the compose file itself only needs copying again when it changes.

Then open `https://<your-domain>/logs` or `https://<your-domain>/analytics` through Caddy and
sign in with any username and that password. Only use HTTPS — Basic auth sends the password
with every request. Watchtower keeps the environment when it recreates the container. Without
the variable both pages return 404 and a warning is logged at startup.

---

## File Structure

```
bingopoker/
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── backend/
│   ├── app.py
│   ├── data/
│   │   ├── users.json
│   │   ├── rooms.json
│   │   ├── analytics.json
│   │   └── .email_pepper       # auto-generated secret — back this up
│   ├── logs/
│   │   ├── bingopoker.log
│   │   └── bingopoker.log.YYYY-MM-DD
│   ├── utils/
│   │   ├── user_manager.py
│   │   ├── room_manager.py
│   │   ├── analytics_manager.py
│   │   ├── file_io.py
│   │   ├── color_palette.py
│   │   └── validators.py
│   ├── routes/
│   │   ├── users.py
│   │   ├── rooms.py
│   │   ├── admin.py
│   │   └── debug.py
│   ├── handlers/
│   │   └── websocket.py
│   └── tests/
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
DATA_DIR=                # defaults to backend/data; a relative path resolves against the working directory
EMAIL_HASH_PEPPER=       # leave empty to auto-generate backend/data/.email_pepper
LOG_DIR=                 # defaults to backend/logs
ADMIN_PASSWORD=          # set to enable /logs and /analytics (HTTPS only)
```

`APP_VERSION` and `BUILD_DATE` are set by the Docker build; outside Docker the app reports
"Development build".

### Email pepper

User emails are stored only as HMAC-SHA256 digests. The pepper used for that digest is read from
`EMAIL_HASH_PEPPER`, or generated once into `backend/data/.email_pepper`. **Back this file up and
keep it out of version control** — losing or changing it orphans every existing user record.

## Troubleshooting

**App won't start: "Module not found"**
```bash
# from the project root
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
2. Back up `backend/data/` (including `.email_pepper` and `analytics.json`).
3. Serve behind HTTPS so WebSocket traffic upgrades to `wss://` and admin credentials are encrypted.
4. Set `ADMIN_PASSWORD` if you want the `/logs` and `/analytics` pages; leave it empty to disable them.
5. Logs rotate daily and 30 files are kept, so no manual log cleanup is needed.

For detailed development info: see [DEVELOPMENT.md](DEVELOPMENT.md)

---

*Last Updated: 2026-10-07*
