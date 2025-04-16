import http.server
import socketserver
import json
import os
import urllib.parse
from pathlib import Path
import re # Regular expressions for parsing SQL
import threading # For locking access to the file
import datetime
import collections # For defaultdict
import traceback # For detailed error printing
from http.cookies import SimpleCookie # <-- Added for login cookies

# --- Configuration ---
BACKEND_DIR = Path(__file__).parent.resolve()
FRONTEND_DIR = (BACKEND_DIR.parent / 'frontend').resolve()
DATA_DIR = (BACKEND_DIR / 'data').resolve()
SQL_FILE_PATH = DATA_DIR / 'tables.sql' # Path to the SQL data file
HOST = 'localhost' # Or '0.0.0.0' to be accessible on your network
PORT = 8000 # Choose a port
SUPPORTED_CLASSES = ['C1', 'C2', 'C3'] # Must match menu.html and initial tables.sql

# --- Login Configuration (Placeholder - INSECURE) ---
# !!! WARNING: This is a placeholder and highly insecure. Use proper password hashing (bcrypt, argon2) in a real app. !!!
USERS_DATA = {
    "admin": "placeholder_hash_admin",
    "teacher1": "placeholder_hash_teacher1"
}
PLACEHOLDER_HASH_TO_PASSWORD = {
    "placeholder_hash_admin": "password123", # Store actual passwords INSECURELY
    "placeholder_hash_teacher1": "teachpass"
}
SESSION_COOKIE_NAME = "ColorDaysSession"
VALID_SESSION_VALUE = "user_is_logged_in_secret_value" # Replace with a secure, random session ID mechanism
# --- End Login Configuration ---


# --- In-Memory Data Store and Lock ---
# Use defaultdict for easier handling of missing keys
# Structure: data_store[class_name][type][points] = count
data_store = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
# Use a Reentrant Lock (RLock) to allow the same thread to acquire the lock multiple times
data_lock = threading.RLock()

# --- SQL File Handling Functions ---

def parse_sql_line(line):
    """Parses a single INSERT statement line."""
    # Regex to capture class_name, type, points, count from the specific INSERT format
    match = re.match(
        r"INSERT INTO counts \(class_name, type, points, count\) VALUES \('([^']*)', '([^']*)', (\d+), (\d+)\);",
        line.strip()
    )
    if match:
        class_name, type_val, points_str, count_str = match.groups()
        try:
            points = int(points_str)
            count = int(count_str)
            return class_name, type_val, points, count
        except ValueError:
            print(f"Warning: Could not parse numbers in line: {line.strip()}")
            return None
    else:
        # Ignore comments and empty lines silently
        if line.strip() and not line.strip().startswith('--'):
             print(f"Warning: Could not parse line format: {line.strip()}")
        return None


def load_data_from_sql():
    """Loads data from tables.sql into the in-memory data_store."""
    global data_store
    print(f"Attempting to load data from: {SQL_FILE_PATH}")
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Use a temporary structure to load into, then swap atomically (within lock)
    temp_data = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
    found_classes = set()
    file_exists = SQL_FILE_PATH.exists()

    if file_exists:
        try:
            with open(SQL_FILE_PATH, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    parsed = parse_sql_line(line)
                    if parsed:
                        class_name, type_val, points, count = parsed
                        # Basic validation of parsed data
                        if 0 <= points <= 6 and type_val in ['student', 'teacher']:
                             temp_data[class_name][type_val][points] = count
                             found_classes.add(class_name)
                        else:
                             print(f"Warning: Invalid data values skipped in line {line_num}: {line.strip()}")

            print(f"Loaded data for classes found in file: {', '.join(sorted(list(found_classes)))}")

        except Exception as e:
            print(f"!!! ERROR reading or parsing {SQL_FILE_PATH}: {e}. Data store might be empty or incomplete.")
            # Optionally clear temp_data if error is severe
            # temp_data.clear()
            # found_classes.clear()

    else:
         print(f"Warning: {SQL_FILE_PATH} not found. Will initialize default data.")

    # Ensure all SUPPORTED_CLASSES have default entries if missing
    needs_save = False
    for class_name in SUPPORTED_CLASSES:
        if class_name not in temp_data: # Check against temp_data, not found_classes
             print(f"Initializing default zero data for missing class: {class_name}")
             needs_save = True # Need to save the defaults we're adding
             for type_val in ['student', 'teacher']:
                 for points_val in range(7): # 0 to 6
                     temp_data[class_name][type_val][points_val] = 0 # Default to 0

    # Update the global data store under lock
    with data_lock:
        data_store = temp_data

    # If we added defaults or the file didn't exist, save the current state
    if needs_save or not file_exists:
        print("Saving initial/default data state to tables.sql...")
        # This call will acquire the RLock again, which is allowed
        if not save_data_to_sql():
             print("!!! CRITICAL: Failed to save initial data. File might be missing or unwritable.")

    print("Data loading/initialization complete.")


def save_data_to_sql():
    """Saves the current in-memory data_store back to tables.sql. Returns True on success, False on failure."""
    global data_store
    print(f"Attempting to save data to: {SQL_FILE_PATH}")
    # Acquire lock. RLock allows acquiring again if the thread already holds it.
    with data_lock:
        try:
            sql_lines = []
            sql_lines.append(f"-- Data saved on {datetime.datetime.now().isoformat()} --")
            sql_lines.append("-- This file is used as the primary data storage. --")
            sql_lines.append("")

            # Iterate through the in-memory store and generate INSERT statements
            # Sort for consistent file output
            for class_name in sorted(data_store.keys()):
                 # Consider only saving SUPPORTED_CLASSES if desired, but saving all is safer
                 for type_val in sorted(data_store[class_name].keys()):
                     for points_val in sorted(data_store[class_name][type_val].keys()):
                         count_val = data_store[class_name][type_val][points_val]
                         safe_class_name = class_name.replace("'", "''") # Basic escaping
                         insert_statement = f"INSERT INTO counts (class_name, type, points, count) VALUES ('{safe_class_name}', '{type_val}', {points_val}, {count_val});"
                         sql_lines.append(insert_statement)

            # --- Enhanced Debugging Around File Write ---
            print(f"DEBUG: About to open {SQL_FILE_PATH} for writing ('w' mode)...")
            # Write the file (overwrite existing)
            with open(SQL_FILE_PATH, 'w', encoding='utf-8') as f:
                print(f"DEBUG: File {SQL_FILE_PATH} opened successfully.")
                f.write("\n".join(sql_lines))
                f.write("\n") # Add a final newline
                print(f"DEBUG: Data written to file buffer.")
            # 'with open' automatically closes the file here, flushing the buffer.
            print(f"Data successfully saved to {SQL_FILE_PATH}") # Success message
            return True

        except PermissionError as e: # Catch specific permission error first
            print(f"!!! PERMISSION ERROR writing to {SQL_FILE_PATH}: {e}")
            print("!!! Please check write permissions for the script/server on the 'data' directory and 'tables.sql' file.")
            return False
        except IOError as e: # Catch other IO errors
            print(f"!!! IO ERROR writing to {SQL_FILE_PATH}: {e}")
            return False
        except Exception as e: # Catch any other unexpected error
            print(f"!!! UNEXPECTED ERROR during save_data_to_sql:")
            print(traceback.format_exc()) # Print full traceback
            return False


# --- HTTP Request Handler ---

class ColorDaysHandler(http.server.BaseHTTPRequestHandler):

    # Helper to parse cookies from request headers
    def get_cookies(self):
        """Parses the Cookie header and returns a SimpleCookie object."""
        cookies = SimpleCookie()
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            cookies.load(cookie_header)
        return cookies

    # Helper to check if user is logged in based on session cookie
    def is_logged_in(self):
        """Checks if a valid session cookie is present."""
        cookies = self.get_cookies()
        session_cookie = cookies.get(SESSION_COOKIE_NAME)
        if session_cookie and session_cookie.value == VALID_SESSION_VALUE:
            return True
        return False

    # Helper to send JSON responses with CORS headers
    def _send_response(self, status_code, data=None, content_type='application/json', headers=None):
        """Sends an HTTP response, handling JSON encoding and CORS headers."""
        try:
            self.send_response(status_code)
            self.send_header('Content-type', content_type)
            # --- CORS Headers ---
            self.send_header('Access-Control-Allow-Origin', '*') # Consider restricting in production
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie') # Allow Cookie header
            self.send_header('Access-Control-Allow-Credentials', 'true') # Needed if frontend sends credentials
            # --- End CORS ---
            if headers:
                for key, value in headers.items():
                    self.send_header(key, value)
            self.end_headers()
            if data is not None:
                response_body = json.dumps(data).encode('utf-8') if content_type == 'application/json' else data
                self.wfile.write(response_body)
        except Exception as e:
            print(f"!!! Error sending response (status {status_code}): {e}")
            # Avoid sending another response if headers already sent etc.

    # Handle CORS preflight requests
    def do_OPTIONS(self):
        self._send_response(204) # No Content for OPTIONS

    # Handle GET requests (serving files and /api/counts)
    def do_GET(self):
        global data_store
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)

        # API Endpoint: /api/counts?class=ClassName
        if path == '/api/counts':
            class_name = query.get('class', [None])[0]
            if not class_name:
                self._send_response(400, {"error": "Missing 'class' query parameter"})
                return

            response_data = []
            # Acquire lock briefly to ensure consistent read
            with data_lock:
                if class_name in data_store:
                    class_data = data_store[class_name]
                    # Format data for JSON response, ensuring all points 0-6 exist
                    for type_val in ['student', 'teacher']:
                        for points_val in range(7): # 0 to 6
                            count = class_data.get(type_val, {}).get(points_val, 0) # Get count, default 0
                            response_data.append({
                                "type": type_val,
                                "points": points_val,
                                "count": count
                            })
                    # Sort for predictable order (optional but good practice)
                    response_data.sort(key=lambda x: (x['type'], x['points']))
                else:
                    # Class not found in memory, return default structure with zeros
                    print(f"Warning: Class '{class_name}' requested via API but not found in memory. Returning zeros.")
                    for type_val in ['student', 'teacher']:
                        for points_val in range(7):
                             response_data.append({"type": type_val, "points": points_val, "count": 0})

            self._send_response(200, response_data)
            return

        # File Serving Logic
        try:
            # Default to menu.html if root path is requested
            # Check for login.html request specifically
            if path == '/login.html':
                 file_path = FRONTEND_DIR / 'login.html'
            elif path == '/':
                 # Redirect root to login page if not logged in, else menu
                 if self.is_logged_in():
                     file_path = FRONTEND_DIR / 'menu.html'
                 else:
                     # Send redirect header
                     self.send_response(302) # Found (redirect)
                     self.send_header('Location', '/login.html')
                     self.end_headers()
                     return # Stop processing further
            else:
                # Construct safe path within FRONTEND_DIR
                safe_subpath = path.lstrip('/')
                # Basic check for potentially malicious paths
                if '..' in safe_subpath:
                     raise FileNotFoundError("Invalid path component '..'")
                file_path = (FRONTEND_DIR / safe_subpath).resolve()

                # Security check: Ensure the resolved path is still within FRONTEND_DIR
                if not file_path.is_relative_to(FRONTEND_DIR):
                     raise FileNotFoundError("Attempted path traversal outside frontend directory")

            if file_path.is_file():
                # Determine content type
                content_type = 'text/plain' # Default
                if file_path.suffix == '.html': content_type = 'text/html'
                elif file_path.suffix == '.css': content_type = 'text/css'
                elif file_path.suffix == '.js': content_type = 'application/javascript'
                elif file_path.suffix == '.json': content_type = 'application/json'
                # Add more types if needed (images, etc.)

                with open(file_path, 'rb') as f:
                    content = f.read()
                self._send_response(200, data=content, content_type=content_type)
            else:
                 # If it's not a file, maybe it's a directory index request? Deny for now.
                 print(f"File not found or is directory: {file_path}")
                 self._send_response(404, {"error": "Resource not found"}, content_type='application/json')

        except FileNotFoundError as e:
            print(f"File serving error (404): {e}")
            self._send_response(404, {"error": "File not found"}, content_type='application/json')
        except Exception as e:
            print(f"!!! Error serving file {path}: {e}")
            print(traceback.format_exc())
            # Avoid sending error if response already started
            try:
                self._send_response(500, {"error": "Internal server error serving file"}, content_type='application/json')
            except:
                 pass # Ignore errors during error reporting


    # Handle POST requests (/login, /api/increment, /api/decrement)
    def do_POST(self):
        global data_store
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0 and path != '/logout': # Allow empty body for logout
             self._send_response(400, {"error": "Empty request body"})
             return
        body = self.rfile.read(content_length)

        # --- LOGIN Endpoint ---
        if path == '/login':
            try:
                credentials = json.loads(body)
                username = credentials.get('username')
                submitted_password = credentials.get('password')

                login_successful = False
                if username in USERS_DATA:
                    # !!! INSECURE PASSWORD CHECK - Replace with hashing !!!
                    placeholder_hash = USERS_DATA[username]
                    expected_password = PLACEHOLDER_HASH_TO_PASSWORD.get(placeholder_hash)
                    if expected_password and submitted_password == expected_password:
                        login_successful = True
                    # !!! END INSECURE CHECK !!!

                if login_successful:
                    # Prepare the session cookie
                    cookie = SimpleCookie()
                    cookie[SESSION_COOKIE_NAME] = VALID_SESSION_VALUE
                    cookie[SESSION_COOKIE_NAME]['path'] = '/' # Make cookie valid for all paths
                    # Optional security attributes (recommended):
                    # cookie[SESSION_COOKIE_NAME]['httponly'] = True # Prevents JS access
                    # cookie[SESSION_COOKIE_NAME]['samesite'] = 'Lax' # CSRF protection
                    cookie_header_val = cookie.output(header='').strip()
                    custom_headers = {'Set-Cookie': cookie_header_val}

                    print(f"Login successful for user: {username}, session cookie set.")
                    self._send_response(200, {"success": True, "message": "Login successful"}, headers=custom_headers)
                else:
                    print(f"Login failed for user attempt: {username}")
                    self._send_response(401, {"error": "Invalid username or password"}) # Unauthorized

            except json.JSONDecodeError:
                 print("Error: Invalid JSON received for login.")
                 self._send_response(400, {"error": "Invalid JSON format in request body"}) # Bad Request
            except Exception as e:
                print(f"Error during login processing: {e}")
                print(traceback.format_exc())
                self._send_response(500, {"error": f"Server error during login"}) # Internal Server Error
            return # Stop processing after handling /login

        # --- LOGOUT Endpoint ---
        elif path == '/logout':
             # Prepare an expired cookie to clear the browser's cookie
             cookie = SimpleCookie()
             cookie[SESSION_COOKIE_NAME] = "" # Clear value
             cookie[SESSION_COOKIE_NAME]['path'] = '/'
             cookie[SESSION_COOKIE_NAME]['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT' # Expire immediately
             cookie[SESSION_COOKIE_NAME]['max-age'] = 0 # Another way to expire
             custom_headers = {'Set-Cookie': cookie.output(header='').strip()}
             print("Logout request received, clearing session cookie.")
             self._send_response(200, {"success": True, "message": "Logged out successfully"}, headers=custom_headers)
             return # Stop processing after handling /logout

        # --- Authentication Check for Protected Endpoints ---
        if not self.is_logged_in():
            print(f"Denied POST request to {path} - User not logged in.")
            self._send_response(401, {"error": "Authentication required"}) # Unauthorized
            return # Stop processing if not logged in
        # --- End Authentication Check ---

        # --- Protected Endpoints (/api/increment, /api/decrement) ---
        print(f"Processing authenticated POST request to {path}...") # Log access

        # Parse JSON body (already read, just need to decode)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_response(400, {"error": "Invalid JSON payload"})
            return

        class_name = data.get('className')
        type_val = data.get('type')
        points_val = data.get('points')

        # Basic validation
        if not all([class_name, type_val, points_val is not None]):
            self._send_response(400, {"error": "Missing data: className, type, or points"})
            return
        if type_val not in ['student', 'teacher']:
            self._send_response(400, {"error": "Invalid type"})
            return
        if not isinstance(points_val, int) or not (0 <= points_val <= 6):
             self._send_response(400, {"error": "Invalid points value"})
             return
        # Maybe validate class_name against SUPPORTED_CLASSES?
        # if class_name not in SUPPORTED_CLASSES:
        #     self._send_response(400, {"error": f"Unsupported class name: {class_name}"})
        #     return

        # --- Critical Section: Modify in-memory data and save to file ---
        success = False
        message = "Operation failed"
        status_code = 500 # Default to internal error
        save_needed = False
        action_verb = "processed" # Default verb

        # Acquire the reentrant lock
        with data_lock:
            try:
                # Use .get() with defaults to safely access potentially missing keys
                current_count = data_store.get(class_name, {}).get(type_val, {}).get(points_val, 0)

                if path == '/api/increment':
                    # Increment in memory using defaultdict's auto-creation
                    data_store[class_name][type_val][points_val] = current_count + 1
                    save_needed = True
                    action_verb = "incremented"

                elif path == '/api/decrement':
                    if current_count > 0:
                        # Decrement in memory
                        data_store[class_name][type_val][points_val] = current_count - 1
                        save_needed = True
                        action_verb = "decremented"
                    else:
                        # Count is already zero, do nothing to file
                        success = False # Operation didn't change state
                        message = "Count already zero"
                        status_code = 400 # Bad Request
                        save_needed = False # No change, no save needed
                else:
                    # Endpoint not found (Shouldn't happen due to checks above, but good practice)
                    success = False
                    message = "API endpoint not found"
                    status_code = 404
                    save_needed = False

                # If an action was performed that requires saving
                if save_needed:
                    print(f"DEBUG: Change detected ({action_verb}), attempting save...")
                    if save_data_to_sql(): # This call acquires the RLock again
                        success = True
                        message = f"Count {action_verb}"
                        status_code = 200
                    else:
                        # Save failed! Critical error.
                        success = False
                        message = f"Count {action_verb} in memory, but CRITICAL error saving to file."
                        status_code = 500 # Internal Server Error

            except Exception as e:
                print(f"!!! UNEXPECTED ERROR during POST {path} operation (within lock):")
                print(traceback.format_exc())
                success = False
                message = "An internal error occurred during the operation."
                status_code = 500
        # --- End Critical Section (Lock Released) ---

        # Send response outside the lock
        if status_code == 200:
             self._send_response(status_code, {"success": success, "message": message})
        else:
             # For errors (4xx, 5xx), send an "error" field instead of "message"
             self._send_response(status_code, {"error": message})

        # --- Handle unknown POST paths ---
        # This part is now implicitly handled because if path is not /login, /logout,
        # /api/increment, or /api/decrement, it will fall through without matching
        # any specific logic after the authentication check. We should add an explicit
        # 404 check if no other path matched.
        # Let's refine the structure slightly for clarity:

        # (Previous code for /login, /logout, auth check remains the same)
        # ...

        # elif path == '/api/increment':
        #     # ... increment logic ...
        #     # Send response
        #     return # Explicitly return after handling

        # elif path == '/api/decrement':
        #     # ... decrement logic ...
        #     # Send response
        #     return # Explicitly return after handling

        # else: # If path wasn't login, logout, increment, or decrement (and user was authenticated)
        #     print(f"Authenticated POST request to unknown path: {path}")
        #     self._send_response(404, {"error": "API endpoint not found"})


# --- Main Execution ---
if __name__ == "__main__":
    print("--- Starting Color Days Server ---")
    # Load initial data from SQL file (or create/initialize if needed)
    load_data_from_sql()

    # Server setup using ThreadingMixIn for basic concurrency
    class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True # Allow shutdown even if threads are running
        allow_reuse_address = True # Allow quick restarts

    httpd = ThreadingHTTPServer((HOST, PORT), ColorDaysHandler)

    print(f"\nServing HTTP on {HOST}:{PORT}...")
    print(f"Frontend root: {FRONTEND_DIR}")
    print(f"Using data file: {SQL_FILE_PATH}")
    print(f"\nAccess the application via: http://{HOST}:{PORT}/")
    print(f"(Will redirect to /login.html if not logged in)")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n--- KeyboardInterrupt received, shutting down server ---")
        # Attempt a final save on shutdown? Can be risky if shutdown is forced.
        # print("Attempting final data save...")
        # if not save_data_to_sql():
        #    print("!!! Warning: Failed to save data on shutdown.")
    finally:
        # Ensure server is properly shut down
        httpd.shutdown()
        httpd.server_close()
        print("--- Server stopped ---")

