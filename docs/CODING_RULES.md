# BingoPoker Coding Rules & Standards

Conventions the codebase actually follows. Apply them to any new code.

---

## File Organization

- **One responsibility per file.** Managers hold state and persistence, routes hold HTTP
  handling, handlers hold WebSocket handling, validators hold validation.
- **Keep modules small.** Existing backend modules are 30–475 lines; split before a module
  becomes a grab bag.
- **Module names reflect content** (`user_manager.py`, `color_palette.py`, `websocket.py`).

Current layout:

```
backend/
├── app.py                  # App factory, config, logging, route wiring
├── routes/                 # users.py, rooms.py, admin.py, debug.py
├── handlers/               # websocket.py
├── utils/                  # user_manager.py, room_manager.py, analytics_manager.py,
│                           # file_io.py, color_palette.py, validators.py
├── tests/                  # conftest.py + test_*.py (pytest)
├── data/                   # users.json, rooms.json, analytics.json, .email_pepper
└── logs/                   # bingopoker.log (+ rotated files); default LOG_DIR

frontend/
├── index.html              # All screens
├── css/styles.css
└── js/                     # api.js (REST client + GridUtils), app.js (everything else)
```

The frontend deliberately uses two JS files; do not introduce a build step or split into
ES modules without changing that decision explicitly.

---

## Python Standards

### Style
- **4-space indentation**, `snake_case` for functions and variables, `PascalCase` for
  classes.
- **Type hints on function signatures**, including `-> None` for procedures.
- **Docstrings** on every module, class and public function; document `Args:` and
  `Returns:` for anything non-trivial.
- **Async/await for I/O.** All handlers are `async`; JSON reads use `aiofiles` and JSON
  writes use `write_json_atomic` (see [Managers](#managers)).
- Private helpers are prefixed with `_` (`_save_to_disk`, `_broadcast`, `_serialize_session`).

### Return conventions
- Validators return `(is_valid: bool, error_message: str | None)`.
- Manager methods return `(success: bool, error: str | None)` or
  `(success: bool, error: str | None, data: dict | None)`.
- Simple lookups (`get_user`, `get_room`) return the object or `None`.

```python
async def update_role(self, email: str, new_role: str) -> tuple[bool, Optional[str]]:
    """
    Update user's role.

    Args:
        email: User email address
        new_role: New role ('worker' or 'observer')

    Returns:
        (success: bool, error: str | None)
    """
```

### Managers
- One manager per resource; managers own both the in-memory cache and the JSON file.
- Data is loaded once during `startup_handler` and managers are stored on the app
  (`app["user_manager"]`, `app["room_manager"]`, `app["analytics_manager"]`). Do not
  create module-level singletons.
- **All JSON persistence goes through the manager classes.** No other module opens
  `users.json`, `rooms.json` or `analytics.json` (`routes/debug.py` is the one deliberate
  exception, and it writes through the manager's own file paths).
- **All JSON writes go through `write_json_atomic`** (`utils/file_io.py`): it serializes
  under a per-file lock, writes `<file>.tmp`, `fsync`s and swaps it in with `os.replace`,
  so a crash never leaves a truncated file. Small text files use `write_text_atomic`.
  Never write a data file in place with `open(..., "w")`.

### Route handlers
- One handler per route, registered in a `setup_*_routes(app)` function.
- Validate inputs first and return early with a JSON error body.
- Error responses use `{"error": "<code>", "message": "<human readable>"}` with status
  400 (bad input), 403 (not the creator), 404 (not found), 409 (duplicate), 500 (server).
- Catch `ValueError` for malformed JSON bodies; keep broad `except Exception` at the
  handler boundary only.

### Logging
- Use the standard `logging` module with a module-level
  `logger = logging.getLogger(__name__)`.
- **Never use `print()`** for diagnostics. (`app.py`'s single startup banner is the only
  intentional console write.)
- **Never log an email address.** Log `user_id` and username instead. Access logging is
  suppressed in `app.py` for the same reason.
- `logger.info` for lifecycle events (registration, room created/deleted, join/leave),
  `logger.warning` for recoverable faults, `logger.error` for failures, `logger.debug` for
  noise like dropped sockets.

---

## JavaScript Standards

### Style
- **4-space indentation**, `camelCase` for functions and variables, `PascalCase` for
  classes and constant collections (`BingoPokerAPI`, `GridUtils`).
- **Vanilla ES6+ only** — `const`/`let`, arrow functions, template literals, optional
  chaining. No frameworks, no npm, no bundler.
- JSDoc-style block comments on API methods and non-obvious helpers.
- State lives in the single `appState` object; screen changes go through `showScreen()`.

### API layer
`api.js` methods never throw at the call site — they return `{ success: true, data }` or
`{ success: false, error }` and log the failure with `console.error`. Callers branch on
`result.success`.

### DOM safety
- **Escape all user-supplied text with `escapeHtml()` before inserting it into the DOM.**
  This applies to usernames, room names and grid cell text.
- **Never interpolate user-supplied text into inline event-handler attributes.** Inline
  `onclick` handlers may only receive server-generated values such as `room_id` or a
  share URL; anything a user typed must be rendered as text content or passed through a
  `addEventListener` closure.
- Prefer `document.createElement` + `textContent` for user data (see `renderBingoGrid`);
  template literals are acceptable for static markup.

### Events
- Handler names start with `handle` (`handleRegister`, `handleCreateRoom`, `handleReveal`).
- Wire form and button listeners once in `setupEventListeners()`.
- WebSocket sends go through `wsSend(type, payload)`; incoming messages are dispatched in
  a single `switch` in `handleWsMessage`.

---

## CSS Standards

- **Theme values live in `:root` custom properties** in `frontend/css/styles.css`; use
  `var(--...)` instead of hard-coded colors.
- Semantic, hyphenated class names describing purpose (`.bingo-cell`, `.room-card`,
  `.user-status`), with state modifiers as separate classes (`.selected`, `.frozen`,
  `.active`, `.hidden`).
- Responsive rules use media queries at the end of the relevant section.
- Bump the `?v=` query string on the `<link>`/`<script>` tags in `index.html` when
  shipping CSS or JS changes.

---

## API Design

### REST
- Resource-oriented paths: `/api/user`, `/api/user/{email}`, `/api/room`,
  `/api/room/{room_id}`, `/api/rooms`.
- Standard verbs: `POST` create, `GET` read, `PUT` update, `DELETE` delete.
- Status codes: 200 ok, 201 created, 400 bad request, 401 unauthenticated socket,
  403 forbidden, 404 not found, 409 conflict, 500 server error.
- Success bodies return the resource directly (`{"user": {...}}`, `{"rooms": [...]}`);
  error bodies use `{"error", "message"}`.

### WebSocket
- Every message is `{"type": "<name>", "payload": {...}}` in both directions.
- Room and user are bound by the connection URL `/ws/{room_id}/{user_email}`; they are not
  repeated in payloads.
- Unknown message types get an `error` message back rather than silent failure.
- Cell coordinates are stored as tuples server-side and serialized to `[row, col]` lists.

---

## Data & Security

- **Never persist an email in plain text.** `users.json` is keyed by a random `uuid4` hex
  ID and stores an HMAC-SHA256 `email_hash`. `rooms.json` stores `created_by` as a user ID.
- **Validate every input server-side**, even when the frontend already checks it.
- Enforce length limits: username 1–50, room name 1–100, grid strictly 5×5 strings, poker
  values restricted to `coffee, 0, 1, 2, 3, 5, 8, 13, 21, split`.
- Only non-sensitive profile data goes in `localStorage` (`bingopoker_user`).
- Destructive debug routes must stay behind the `DEBUG` flag.
- Admin pages stay behind `ADMIN_PASSWORD` (HTTP Basic auth, constant-time comparison,
  served only over HTTPS). Never accept a file path from the request — serve only names
  from a server-built list.
- Analytics store aggregate counts only — no emails or usernames.
- Use `wss://` automatically when the page is served over HTTPS (`connectWebSocket`
  already derives the scheme from `location.protocol`).

---

## Documentation

- Comments explain **why**, not what, and stay to a single line where possible.
- Keep `README.md` and the markdown docs in `docs/` in sync when behaviour changes.
- Python docstrings follow the `Args:` / `Returns:` form used throughout `utils/`.

---

## Testing

- Tests live in `backend/tests/` and use `pytest` with `pytest-aiohttp` (declared in the
  root `requirements-dev.txt`; configuration in the root `pytest.ini`). Run them from the
  repository root with `pip install -r requirements-dev.txt` and `pytest`.
- Build the app through the `client` fixture in `conftest.py`, which calls
  `create_app(data_dir=..., log_dir=..., admin_password=...)` with temporary directories.
  Tests must never read or write `backend/data` or `backend/logs`.
- Use synthetic data only (e.g. `<name>@example.test`).
- Name tests `test_<behaviour>` and follow Arrange-Act-Assert.
- Add or update a test with every backend behaviour change. The CI `test` job runs
  `pytest` on every push to `main`, and the Docker image is only published when it passes.
- UI behaviour is still verified manually: exercise registration, room creation,
  multi-user join, reveal and reset in the browser, and check the log file and the
  DevTools console for errors.

> This repository has no linter, formatter or pre-commit hook. Style rules above are
> enforced by review, not tooling; CI only runs the tests.

---

## Review Checklist

- [ ] Follows the conventions in this document
- [ ] Inputs validated server-side, user text escaped before DOM insertion
- [ ] No email in logs, no plain email persisted
- [ ] Managers own all JSON reads/writes, and writes go through `write_json_atomic`
- [ ] Errors returned as structured JSON with an appropriate status code
- [ ] Tests added or updated, and `pytest` passes
- [ ] Docs updated if behaviour changed
- [ ] Manually verified in the browser (no console errors)

---

*Last Updated: 2026-10-07*
