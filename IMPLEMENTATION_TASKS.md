# BingoPoker Implementation Status

Status snapshot of what is built and what is still missing. For behaviour details see
[API_SPECIFICATIONS.md](API_SPECIFICATIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md) and
[DATA_STRUCTURES.md](DATA_STRUCTURES.md).

---

## Completed

### Backend
- [x] aiohttp application factory with startup/cleanup hooks, health check, and static
      serving of `frontend/` (`backend/app.py`).
- [x] Environment configuration via `python-dotenv`: `HOST`, `PORT`, `DEBUG`, `DATA_DIR`,
      `EMAIL_HASH_PEPPER`.
- [x] Structured logging to `backend/logs/bingopoker.log` (file `INFO`, console `WARNING`),
      with aiohttp access logs suppressed so emails never reach the log.
- [x] `UserManager`: registration, lookup, username and role updates, JSON persistence.
      Users are keyed by a random `uuid4` hex ID and identified by an HMAC-SHA256 email
      digest; plain emails are never persisted. Legacy email-keyed records are migrated on
      load.
- [x] Auto-generated HMAC pepper stored at `<DATA_DIR>/.email_pepper` when
      `EMAIL_HASH_PEPPER` is unset.
- [x] `RoomManager`: room creation with generated `room-XXXXXXXX` IDs, 5×5 grid config
      persistence, in-memory session state, bingo/poker selection recording, reveal,
      reset, deletion, and migration of legacy email `created_by` values to user IDs.
- [x] `ColorPalette` with 10 contrasting colors and `get_color_by_index(index)`; rooms
      assign colors from a monotonic `color_counter` so rejoining users do not collide.
- [x] `Validators` for email, username (1–50), room name (1–100), room ID format, 5×5
      grid, and poker values (`0, 1, 2, 3, 5, 8, 13, 21, split`).
- [x] User REST API: `POST /api/user`, `GET /api/user/{email}`, `PUT /api/user/{email}`.
- [x] Room REST API: `POST /api/room` (duplicate names rejected with 409),
      `GET /api/room/{room_id}`, `GET /api/rooms`, `DELETE /api/room/{room_id}`
      restricted to the room creator (403 otherwise).
- [x] WebSocket endpoint `/ws/{room_id}/{user_email}` handling join, `bingo_select`,
      `poker_select`, `reveal`, `reset` and disconnect, with per-room broadcast, cleanup
      of dead connections, and a `replaced` message when the same user reconnects.
- [x] Debug endpoints `DELETE /api/debug/users` and `DELETE /api/debug/rooms`, mounted
      only when `DEBUG=true`.

### Frontend
- [x] Single-page `index.html` with login modal, room-select screen and game screen.
- [x] Registration and login by email + username, with role selection (worker/observer)
      and profile caching in `localStorage`.
- [x] Role switching from the room-select screen (`PUT /api/user/{email}`).
- [x] Room list with participant counts, join buttons, copy-to-clipboard invite links and
      a Remove button shown only to the room creator.
- [x] Room creation with three grid sources: the built-in default template, an empty 5×5
      editor, and JSON import (`frontend/templates/agile-default.json` is a valid import).
- [x] Grid configuration download from inside a room.
- [x] Deep-link sharing via `?r=<room_id>`, including `pending_room` handoff for visitors
      who must register first, and browser back/forward handling via `popstate`.
- [x] Live game rendering: bingo grid with per-user color dots, poker value buttons,
      participant list with status, reveal/reset controls and a post-reveal average
      summary.
- [x] Visibility rules: observer selections always visible, worker selections private
      until reveal.
- [x] WebSocket client with message dispatch and connection-error handling; failed REST
      calls surface as inline errors or alerts rather than silent failures.
- [x] HTML escaping of all user-supplied text before DOM insertion.
- [x] `?dev=true` flag to reveal the debug buttons.

---

## Remaining Work

- [ ] **No automated tests.** `backend/tests/` is empty; `pytest` and `pytest-aiohttp` are
      declared in `backend/requirements-dev.txt` but unused. All verification is manual.
- [ ] **No authentication.** Identity is a self-asserted email + username; anyone who
      knows an email can act as that user. There is no password, token or session check.
- [ ] **Single-process, in-memory session state.** Active participants, selections and
      the reveal flag live in one process's memory, so the app cannot be scaled
      horizontally and all sessions are lost on restart.
- [ ] **No rate limiting** on REST endpoints or WebSocket messages.
- [ ] **No log rotation.** `backend/logs/bingopoker.log` grows without bound.
- [ ] **Colors repeat after 10 participants** in a room, since the palette holds 10 colors
      and the counter wraps.

---

*Last Updated: 2026-08-18*
