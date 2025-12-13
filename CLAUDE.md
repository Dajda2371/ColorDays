# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ColorDays is a web application for an elementary school in Štěnovice, Czech Republic. It manages a tradition where students wear specific colors on the three days before Easter and earn points for it. The system simplifies counting and tracking these points across classes.

## Architecture

### Backend Structure (Python)

The backend has recently been refactored from a monolithic `program.py` into a modular structure:

- **program.py** - Entry point that sets up logging, initializes the server, and handles graceful shutdown via 'stop' command
- **server.py** - HTTP request handler (`ColorDaysHandler`) that processes all API endpoints and serves static files
- **data_manager.py** - Database operations, in-memory data stores (`class_data_store`, `students_data_store`, `user_password_store`), and migration logic
- **config.py** - Configuration constants including paths, OAuth settings, security parameters, and role definitions
- **auth.py** - User authentication helpers for determining current user identity and role
- **utils.py** - Utility functions for password hashing (PBKDF2-HMAC-SHA256), random code generation, and cookie management

### Data Storage

The application uses SQLite databases with a year-based organization:

- **backend/data/data.db** - Global database containing users and tokens tables
- **backend/data/{year}/{year}.db** - Year-specific database containing classes, students, and counts tables
- Legacy .sql files still exist for migration purposes

Year-specific data is organized in `backend/data/2025/` (dynamically determined by current year).

### Frontend Structure (Vanilla JS)

The frontend is plain HTML/CSS/JavaScript with no framework:

- Each page has its own HTML and JS file (e.g., `login.html` + `login.js`)
- Main pages: `index.html` (point counting), `classes.html`, `students.html`, `config.html`, `menu.html`, `login.html`, `change-password.html`
- Communication with backend via REST API

### Authentication & Authorization

The system supports multiple authentication methods:

1. **Password-based login** - Uses PBKDF2-HMAC-SHA256 hashing with salt
2. **Google OAuth** - Users marked with `_GOOGLE_AUTH_USER_` as password_hash
3. **Student codes** - Random 15-character alphanumeric codes for student access

Three user roles exist:
- `administrator` - Full access
- `teacher` - Standard teacher access
- Student sessions - Limited access via student codes

Special password states in the database:
- `_NULL_` or `NOT_SET` - Password not yet configured
- `_password_` (wrapped in underscores) - Temporary password requiring change on first login
- `salt:hash` - Standard PBKDF2 hashed password
- `_GOOGLE_AUTH_USER_` - OAuth user (cannot set password)

### Data Model

**Classes Table:**
- Defines which class counts on which day (counts1, counts2, counts3)
- Defines which class is counted by which class on each day (iscountedby1, iscountedby2, iscountedby3)

**Students Table:**
- Each student has a unique code for authentication
- `counts_classes` field stores a string like `[Class1,Class2]` listing which classes this student counts
- `note` field typically contains student name or identifier

**Counts Table:**
- Stores point counts per class, per day, per type (student/teacher), per points (0-6)

### Threading & Concurrency

- Server runs in a daemon thread (`server_thread`)
- Main thread handles user input for graceful shutdown
- All data store access is protected by `data_lock` (RLock) in data_manager.py

## Development Commands

### Running the Server

```bash
python backend/program.py
# or use the convenience script:
./start.sh
```

The server runs on `http://localhost:8000` by default. Type 'stop' and press Enter to gracefully shutdown.

### Installing Dependencies

```bash
pip install --upgrade google-auth-oauthlib google-api-python-client requests
```

The server will attempt to auto-install missing Google OAuth dependencies on startup if not present.

### Database Schema and Migration

Schema files define the database structure:
- `backend/data/schema.sql` - Users and tokens tables
- `backend/data/{year}/schema.sql` - Classes, students, and counts tables

Migration functions in `data_manager.py` handle conversion from legacy .sql files to SQLite databases:
- `migrate_logins_to_db()` - Migrates logins.sql to data.db
- `migrate_tokens_to_db()` - Migrates tokens.sql to data.db
- `migrate_classes_to_db()` - Migrates classes.sql to {year}.db
- `migrate_students_to_db()` - Migrates students.sql to {year}.db
- `migrate_counts_to_db()` - Migrates tables-*.sql (count data) to {year}.db

To run migrations: `python3 backend/migrate_to_db.py`

## Key API Endpoints

All API endpoints require authentication unless otherwise noted:

**User Management:**
- GET `/api/users` - List users (admin only)
- POST `/api/users` - Add new user
- POST with `action: "remove_user"` - Remove user (admin only, cannot remove 'admin')
- POST with `action: "reset_password"` - Reset user password (not allowed for OAuth users)

**Class/Student Data:**
- GET `/api/classes` - List all classes (admin/teacher/students)
- GET `/api/students` - List students (filtered for student sessions)
- GET `/api/student/counting-details?code={code}&day={1|2|3}` - Student counting assignment details
- GET `/api/counts?class={class}&day={monday|tuesday|wednesday}` - Get counts for specific class/day
- POST `/api/counts` - Update counts

**Configuration:**
- GET `/api/data/config` - Server configuration including domain and port
- GET `/api/translations` - Language translations JSON

**Authentication:**
- GET `/login/google` - Initiate Google OAuth flow
- GET `/oauth2callback` - OAuth callback handler

## Important Patterns

### Security Checks for Students

The `is_student_allowed()` function enforces that students can only:
1. View/modify classes they're assigned to count (via `counts_classes` field)
2. On days when their main class is designated to supervise (via `iscountedby{1|2|3}` fields)

### Cookie-Based Sessions

Sessions use multiple cookies:
- `ColorDaysSession` - Main session validity marker
- `ColorDaysUser` - Username display
- `GoogleAuthUser` - OAuth user identifier
- `SQLAuthUser` - SQL-based user identifier
- `SQLAuthUserStudent` - Student code for student sessions
- `ChangePasswordVerificationNotNeeded` - Tracks if password change is required

### Logging

Logs are stored in `backend/data/logs/{date}.log` with both file and console output. The logging system redirects stdout/stderr through a custom `StreamToLogger` class.

### Year-Based Data Organization

The `CURRENT_YEAR_DIR` is automatically set to `backend/data/{current_year}/`. Database files and count tables are organized per year to maintain historical data separation.
