# GET API Endpoints

This directory contains all GET endpoint handlers for the ColorDays API, organized by functionality for better maintainability and readability.

## File Structure

```
backend/api/get/
├── __init__.py          # Aggregates all routes into GET_ROUTES dictionary
├── users.py             # User management endpoints
├── classes.py           # Class listing endpoint
├── students.py          # Student management and counting details endpoints
├── counts.py            # Count data retrieval endpoint
├── config.py            # Server configuration endpoint
├── translations.py      # Language translations endpoint
├── oauth.py             # Google OAuth authentication endpoints
└── README.md            # This file
```

## Endpoints by File

### users.py
- **GET /api/users** - List all users (Admin only)

### classes.py
- **GET /api/classes** - List all classes (Admin, Teacher, or Student)

### students.py
- **GET /api/students** - List all students (Admin, Teacher, or Student)
- **GET /api/student/counting-details** - Get detailed counting information for a student (Admin or Teacher)

### counts.py
- **GET /api/counts** - Get count data for a specific class and day (Admin, Teacher, or authorized Student)

### config.py
- **GET /api/data/config** - Get server configuration (Public)

### translations.py
- **GET /api/translations** - Get language translations (Public)

### oauth.py
- **GET /login/google** - Initiate Google OAuth login flow (Public)
- **GET /oauth2callback** - Handle Google OAuth callback (Public)

## Usage

All routes are aggregated in the `GET_ROUTES` dictionary in `__init__.py`. To use in server.py:

```python
from api import GET_ROUTES

# In do_GET method:
if path in GET_ROUTES:
    GET_ROUTES[path](handler)
    return
```

## OAuth Dependencies

The oauth.py module requires Google OAuth libraries to be set by server.py:

```python
from api.get import set_oauth_dependencies

# After importing Google libraries in server.py:
set_oauth_dependencies(InstalledAppFlow, google_discovery_service)
```

## Adding New GET Endpoints

1. Create a new file or add to an existing file in this directory
2. Import necessary dependencies from config, auth, data_manager, and utils
3. Define your handler function(s)
4. Import the handler in `__init__.py`
5. Add the route to the `GET_ROUTES` dictionary
6. Update this README with the new endpoint

## Notes

- All handlers receive a `handler` parameter (the ColorDaysHandler instance)
- Use `handler._send_response()` for sending JSON responses
- Access cookies via `handler.get_cookies()`
- Check authentication via `handler.is_logged_in()`
- Use `data_lock` when accessing shared data stores
