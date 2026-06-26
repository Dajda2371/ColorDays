# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ColorDays is a web application for an elementary school in Štěnovice, Czech Republic. It manages a tradition where students wear specific colors on the three days before Easter and earn points for it. The system simplifies counting and tracking these points across classes.

## Architecture

### Backend (Python / FastAPI)

The backend is a **FastAPI** application served by **Uvicorn**. (Note: legacy `server.py` and the `http.server`-based handler it contained are no longer the runtime; `program.py` now just launches Uvicorn. Some docs/README files elsewhere in the tree still describe the old `ColorDaysHandler`/`GET_ROUTES` design — treat those as stale.)

- **main.py** - The FastAPI `app`. Defines middleware, CORS, the lifespan startup hook (loads all data stores and creates DB tables), dynamic router loading, protected-page serving, and the static file mount. This is the real entry point (`main:app`).
- **program.py** - Thin wrapper that calls `uvicorn.run("main:app", ...)` using `HOST`/`PORT` from config.
- **data_manager.py** - SQLite operations, the in-memory data stores (`class_data_store`, `students_data_store`, `user_password_store`, `server_config`, `overrides_store`), the global `data_version` counter, and legacy `.sql` → SQLite migration functions.
- **dependencies.py** - FastAPI dependency-injection auth helpers (`get_current_user_info`, `get_current_user`, `get_current_admin_user`) and the in-memory `active_sessions` dict. Also gates optional Google OAuth imports.
- **config.py** - Constants: paths, `DOMAIN`/`HOST`/`PORT` (8000), OAuth settings, PBKDF2 parameters, role names, cookie names, `REFRESH_INTERVALS`, and DB file paths.
- **utils.py** - Password hashing (PBKDF2-HMAC-SHA256), random code generation, cookie helpers.
- **auth.py** - Older auth helpers (still present; most request auth now flows through `dependencies.py`).

### Dynamic Router Loading (important)

API endpoints are **not** registered manually. At startup, `include_routers_recursively(app, BACKEND_DIR / "api")` walks the `backend/api/` tree, imports every `.py` file that exposes a module-level `router` (an `APIRouter`), and includes it. The directory layout mirrors HTTP method then resource:

```
backend/api/{get,post,put,delete}/{resource}/{handler}.py
```

To **add an endpoint**: create a file under the appropriate `backend/api/<method>/<resource>/` folder, define `router = APIRouter()`, and decorate a handler (e.g. `@router.get("/api/...")`). It is picked up automatically on next startup — no central registration. The full path string lives in the decorator, so the folder is organizational only; most paths are `/api/...` but auth/login paths (`/login`, `/login/student`, `/login/google`, `/logout`, `/oauth2callback`) are not prefixed.

### Data Storage

SQLite, organized by year. **Database files live directly under `backend/data/`** (not in per-year subdirectories):

- **backend/data/data.db** - Global DB: `users` and `tokens` tables (see `schema.sql`).
- **backend/data/{year}.db** - Year-specific DB, e.g. `2025.db`, `2026.db`: `classes`, `students`, `counts_monday`/`counts_tuesday`/`counts_wednesday`, and `overrides` tables (see `schema_year.sql`). `YEAR_DATABASE_FILE` resolves to the current calendar year automatically.
- **backend/data/config.json** - Main server config (loaded into `server_config`, includes `default_language`).
- **backend/data/overrides.json** - Legacy; overrides now live in the `overrides` table of the year DB.
- **backend/data/client_secret.json** - Google OAuth client secret.

Legacy `.sql` files (under `backend/data/folder/` and old year dirs) exist only for migration.

### Frontend (Vanilla JS)

Plain HTML/CSS/JS, no framework. Each page has its own HTML + JS file. Pages: `index.html` (point counting, with `script.js`), `classes.html`, `students.html`, `config.html`, `overides.html` (admin overrides — note the spelling), `leaderboard.html`, `menu.html`, `login.html`, `change-password.html`, `student-is-counting.html`. Shared styling in `style.css`. Communication is via the REST API. Pages auto-refresh on intervals defined in `config.REFRESH_INTERVALS` and served via `/api/config/refresh_intervals`; clients also poll `/api/data/version` to detect data changes.

### Authentication & Authorization

Auth is cookie-based and resolved per request through `dependencies.get_current_user_info`, which checks for a valid session cookie then maps an identity cookie to `user_password_store`.

Auth methods:
1. **Password login** - PBKDF2-HMAC-SHA256 with salt.
2. **Google OAuth** - users stored with `_GOOGLE_AUTH_USER_` as their password hash.
3. **Student codes** - random 15-char alphanumeric codes; student sessions are limited.

Roles: `administrator` (full), `teacher` (standard), and student sessions (restricted). `get_current_admin_user` is the dependency that enforces admin-only endpoints.

Special password-hash states in the DB:
- `_NULL_` / `NOT_SET` - not yet configured
- `_password_` (wrapped in underscores) - temporary password, forces a change on first login
- `salt:hash` - standard PBKDF2 hash
- `_GOOGLE_AUTH_USER_` - OAuth user (cannot set a password)

### Middleware (main.py)

Three HTTP middlewares run on every request:
- **language_cookie_middleware** - sets a default `language` cookie when missing.
- **force_password_change_middleware** - if the `ChangePasswordVerificationNotNeeded` cookie is set, blocks all routes except an allowlist (change-password page, logout, translations, auth, static assets), returning 403 for API calls or redirecting pages.
- **concurrency_lock_middleware** - serializes all write requests (`POST`/`PUT`/`DELETE`/`PATCH`) behind a single `asyncio.Lock` (`global_write_lock`). In-memory store access in `data_manager` is additionally guarded by `data_lock` (an `RLock`).

### Data Model

**classes** (`class` PK): `teacher`, `counts1/2/3` (which class counts on each day), `iscountedby1/2/3` (which class supervises it each day), `state1/2/3` (per-day class state, e.g. locked).

**students** (`code` PK): `class` (main class), `note` (typically the student name), `counts_classes` (a string like `[Class1,Class2]` of classes this student counts).

**counts_{monday,tuesday,wednesday}** (PK `class_name,type,points`): `type` is `student`/`teacher`, `points` 0–6, `count` is the tally.

**overrides** (PK `class_name,day`): `config_json` blob — admin overrides for leaderboard scores / class availability with custom styling and icons.

## Development Commands

### Running the Server

```bash
./start.sh          # cd backend, activate .venv, run uvicorn main:app --reload (port from config.py)
# or:
python backend/program.py   # same app via uvicorn (reload=True)
```

Server listens on `http://localhost:8000` by default. With `--reload`, code changes restart automatically.

### Dependencies

```bash
pip install -r backend/requirements.txt
```
(`fastapi`, `uvicorn`, `requests`, `google-auth-oauthlib`, `google-api-python-client`, `pytest`, `httpx`). Google OAuth libs are optional at import time — the app degrades gracefully if they're missing (`GOOGLE_OAUTH_AVAILABLE`).

### Tests

Tests live in `backend/tests/` and use **pytest** with FastAPI's `TestClient`. `conftest.py` provides `client` and `admin_client` fixtures that reset the in-memory stores and simulate a logged-in admin via cookies.

```bash
cd backend
python -m pytest                       # run all tests
python -m pytest tests/test_api.py     # single file
python -m pytest tests/test_auth.py::<test_name>   # single test
```

Note: `backend/tests/` also contains various one-off `.py`/`.js` maintenance/translation scripts (e.g. `add_translations*.py`, `check_*.js`) that are not pytest tests.

### Admin Setup

```bash
python backend/setup_admin.py        # create/update the 'admin' user (prompts for password)
# or the wrappers in setup/: setup_admin.sh / setup_admin.cmd
```

### Migration (legacy .sql → SQLite)

```bash
python3 backend/migrate_to_db.py
```
Driven by the `migrate_*_to_db()` functions in `data_manager.py` (`migrate_logins_to_db`, `migrate_tokens_to_db`, `migrate_classes_to_db`, `migrate_students_to_db`, `migrate_counts_to_db`).

### Docker

```bash
docker compose up --build    # builds from Dockerfile, maps 8000:8000, volume-mounts ./backend/data
```
If you change `PORT` in `config.py`, update the port mapping in `docker-compose.yml` too.

## Key API Endpoints

Paths come from the router decorators (folder = organization only). Selected endpoints:

**Auth:** `POST /login`, `POST /login/student`, `GET /login/google`, `GET /oauth2callback`, `POST /logout`, `POST /api/auth/change`, `GET /api/auth/me`

**Users (admin):** `GET /api/users`, `POST /api/users`, `PUT /api/users/role`, `DELETE /api/users`

**Classes:** `GET /api/classes`, `POST /api/classes`, `DELETE /api/classes`, `DELETE /api/classes/assignments`, `PUT /api/classes/counts`, `PUT /api/classes/iscountedby`, `PUT /api/classes/iscountedby/batch`, `POST /api/classes/prefill`

**Students:** `GET /api/students`, `POST /api/students`, `DELETE /api/students`, `GET /api/student/counting-details`, `PUT /api/student/counting-class`

**Counts:** `GET /api/counts?class={class}&day={monday|tuesday|wednesday}`, `POST /api/increment`, `POST /api/decrement`, `PUT /api/counts/state`

**Leaderboard / Overrides:** `GET /api/leaderboard`, `GET /api/overrides`, `POST /api/overrides`

**Config / i18n:** `GET /api/data/config`, `GET /api/config/public`, `POST /api/data/save/config`, `GET /api/config/refresh_intervals`, `GET /api/data/version`, `GET /api/translations`, `POST /api/language/set`

## Important Patterns

### Student Authorization

`is_student_allowed(student_code, class_name, day)` in `data_manager.py` enforces that a student may only view/modify classes listed in their `counts_classes`, and only on days their main class is the supervisor (via the `iscountedby{1|2|3}` columns). Always call it for student-session requests touching count data.

### Cookies / Sessions

Session validity comes from `ColorDaysSession` (`VALID_SESSION_VALUE` or a token in `active_sessions`). Identity is resolved in priority order from `SQLAuthUser` → `GoogleAuthUser` → `ColorDaysUser`. Other cookies: `SQLAuthUserStudent` (student code for student sessions), `GoogleAuthUser` (OAuth id), `ChangePasswordVerificationNotNeeded` (forces password change), `language`.

### Static & Protected Pages

`main.py` mounts the whole `frontend/` directory at `/`. A set of HTML pages (`/`, `index.html`, `menu.html`, `classes.html`, `config.html`, `overides.html`, `students.html`, `change-password.html`, `leaderboard.html`) are served through a guarded handler that enforces login, admin-only access (`config.html`, `overides.html`), student restrictions, and forced password change before returning the file.

### Data Version Counter

Mutations call `increment_data_version()`; the frontend polls `GET /api/data/version` to know when to refresh, avoiding constant full reloads.
