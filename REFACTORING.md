# API Endpoint Refactoring Plan

## Current Status

✅ **Completed:**
- Created `backend/api/` directory
- Created `backend/api/get.py` with all GET endpoint handlers
- Organized GET endpoints into reusable functions

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

### api/post.py (TODO)
Should contain POST endpoint handlers organized by category:

**Authentication:**
- POST /login - Username/password login
- POST /login/student - Student code login
- POST /logout - Logout
- POST /api/auth/change - Change password

**User Management:**
- POST /api/users - Add user
- POST /api/users/remove - Remove user
- POST /api/users/set - Set password
- POST /api/users/reset - Reset password

**Class Management:**
- POST /api/classes/add - Add class
- POST /api/classes/remove - Remove class
- POST /api/classes/update_counts - Update counting days
- POST /api/classes/update_iscountedby - Update counting assignments

**Student Management:**
- POST /api/students/add - Add student
- POST /api/students/remove - Remove student
- POST /api/student/update-counting-class - Update counting assignment

**Count Data:**
- POST /api/increment - Increment count
- POST /api/decrement - Decrement count

**Configuration:**
- POST /api/data/save/config - Save config
- POST /api/language/set - Set language

## Integration with server.py

### Current do_GET method:
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

### Proposed do_POST method:
```python
def do_POST(self):
    parsed_path = urllib.parse.urlparse(self.path)
    path = parsed_path.path

    # Check POST_ROUTES from api.post
    if path in POST_ROUTES:
        POST_ROUTES[path](self)
        return

    # 404 for unknown endpoints
    self._send_response(404, {"error": "Endpoint not found"})
```

## Benefits

1. **Modularity:** Each endpoint is a self-contained function
2. **Testability:** Easy to unit test individual endpoints
3. **Maintainability:** Changes to one endpoint don't affect others
4. **Readability:** Clear organization by HTTP method and category
5. **Reusability:** Functions can be imported and reused elsewhere

## Next Steps

1. Create `api/post.py` with all POST handlers
2. Update `server.py` to use the route mappings
3. Test all endpoints to ensure functionality is preserved
4. Update `CLAUDE.md` with new architecture
