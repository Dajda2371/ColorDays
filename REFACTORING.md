# API Endpoint Refactoring Plan

## Current Status

✅ **Completed:**
- Created `backend/api/` directory
- Created `backend/api/get.py` with all GET endpoint handlers (9 endpoints)
- Created `backend/api/post.py` with all POST endpoint handlers (18 endpoints)
- Organized all endpoints into reusable functions with route mappings
- Created `backend/api/__init__.py` for easy imports

## Structure

### api/get.py (DONE)
Contains all GET endpoint handlers organized as functions:
- `handle_api_users()` - GET /api/users
- `handle_api_classes()` - GET /api/classes
- `handle_api_students()` - GET /api/students
- `handle_api_student_counting_details()` - GET /api/student/counting-details
- `handle_api_counts()` - GET /api/counts
- `handle_api_data_config()` - GET /api/data/config
- `handle_api_translations()` - GET /api/translations
- `handle_login_google()` - GET /login/google
- `handle_oauth2callback()` - GET /oauth2callback

Route mapping dictionary: `GET_ROUTES`

### api/post.py (DONE)
Contains all POST endpoint handlers organized by category:

**Authentication:**
- `handle_login()` - POST /login
- `handle_login_student()` - POST /login/student
- `handle_logout()` - POST /logout
- `handle_auth_change()` - POST /api/auth/change

**User Management:**
- `handle_api_users_post()` - POST /api/users
- `handle_api_users_remove()` - POST /api/users/remove
- `handle_api_users_set()` - POST /api/users/set (also handles /api/users/reset)

**Class Management:**
- `handle_api_classes_add()` - POST /api/classes/add
- `handle_api_classes_remove()` - POST /api/classes/remove
- `handle_api_classes_update_counts()` - POST /api/classes/update_counts
- `handle_api_classes_update_iscountedby()` - POST /api/classes/update_iscountedby

**Student Management:**
- `handle_api_students_add()` - POST /api/students/add
- `handle_api_students_remove()` - POST /api/students/remove
- `handle_api_student_update_counting_class()` - POST /api/student/update-counting-class

**Count Data:**
- `handle_api_increment()` - POST /api/increment
- `handle_api_decrement()` - POST /api/decrement

**Configuration:**
- `handle_api_data_save_config()` - POST /api/data/save/config
- `handle_api_language_set()` - POST /api/language/set

Route mapping dictionary: `POST_ROUTES`

## Integration with server.py

### Proposed Changes:

**Step 1: Import route mappings at top of server.py**
```python
from api import GET_ROUTES, POST_ROUTES
```

**Step 2: Simplify do_GET method**
```python
def do_GET(self):
    parsed_path = urllib.parse.urlparse(self.path)
    path = parsed_path.path

    # Check GET_ROUTES from api.get
    if path in GET_ROUTES:
        GET_ROUTES[path](self)
        return

    # Fall back to file serving...
```

**Step 3: Simplify do_POST method**
```python
def do_POST(self):
    parsed_path = urllib.parse.urlparse(self.path)
    path = parsed_path.path

    # Handle special endpoints that don't need auth or JSON parsing
    if path in ['/login', '/login/student', '/logout']:
        POST_ROUTES[path](self)
        return

    # --- Password Change Check for POST ---
    cookies = self.get_cookies()
    password_change_required = cookies.get(CHANGE_PASSWORD_COOKIE_NAME)
    allowed_post_paths_during_change = ['/login', '/logout', '/api/auth/change']

    if password_change_required and password_change_required.value == "not-required" and path not in allowed_post_paths_during_change:
        print(f"Denied POST request to {path} - Password change required.")
        self._send_response(403, {"error": "Password change required before performing this action."})
        return

    # --- RBAC: Get current user's role for protected endpoints ---
    user_key_for_rbac, current_user_role = get_current_user_info(self)
    if not self.is_logged_in():
        self._send_response(401, {"error": "Authentication required for this action."})
        return

    # --- Parse JSON body ---
    content_length = int(self.headers.get('Content-Length', 0))
    post_body_bytes = b''
    if content_length > 0:
        post_body_bytes = self.rfile.read(content_length)

    try:
        if not post_body_bytes:
            self._send_response(400, {"error": "Missing JSON payload for this endpoint"})
            return
        data = json.loads(post_body_bytes)
    except json.JSONDecodeError:
        self._send_response(400, {"error": "Invalid JSON payload"})
        return

    # Check POST_ROUTES
    if path in POST_ROUTES:
        # Some handlers need the data parameter
        if path in ['/api/auth/change', '/api/users/remove', '/api/users/set', '/api/users/reset',
                    '/api/classes/add', '/api/classes/remove', '/api/classes/update_counts',
                    '/api/classes/update_iscountedby', '/api/students/add', '/api/students/remove',
                    '/api/student/update-counting-class', '/api/increment', '/api/decrement',
                    '/api/data/save/config', '/api/language/set', '/api/users']:
            POST_ROUTES[path](self, data)
        else:
            POST_ROUTES[path](self)
        return

    # 404 for unknown endpoints
    self._send_response(404, {"error": "API endpoint not found"})
```

## Benefits

1. **Modularity:** Each endpoint is a self-contained function
2. **Testability:** Easy to unit test individual endpoints
3. **Maintainability:** Changes to one endpoint don't affect others
4. **Readability:** Clear organization by HTTP method and category
5. **Reusability:** Functions can be imported and reused elsewhere

## Next Steps

1. ✅ ~~Create `api/post.py` with all POST handlers~~ - DONE
2. 🔄 Update `server.py` to use the route mappings (ready to integrate)
3. ⏳ Test all endpoints to ensure functionality is preserved
4. ⏳ Update `CLAUDE.md` with new architecture
5. ⏳ Remove old handler methods from ColorDaysHandler class in server.py
