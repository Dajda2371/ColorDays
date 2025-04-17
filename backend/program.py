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
import hashlib # <-- Use built-in hashlib
import hmac # <-- Use built-in hmac for secure comparison
import os      # <-- Use built-in os for random salt
import binascii # <-- For converting bytes to hex and back

# --- Configuration ---
BACKEND_DIR = Path(__file__).parent.resolve()
FRONTEND_DIR = (BACKEND_DIR.parent / 'frontend').resolve()
DATA_DIR = (BACKEND_DIR / 'data').resolve()
SQL_FILE_PATH = DATA_DIR / 'tables.sql' # Path to the SQL data file
LOGINS_SQL_FILE_PATH = DATA_DIR / 'logins.sql' # Path to the SQL logins file <--- NEW
HOST = 'localhost' # Or '0.0.0.0' to be accessible on your network
PORT = 8000 # Choose a port
SUPPORTED_CLASSES = ['C1', 'C2', 'C3'] # Must match menu.html and initial tables.sql

# --- Secure Login Configuration (Using hashlib.pbkdf2_hmac) ---

# Parameters for PBKDF2
HASH_ALGORITHM = 'sha256'
# Iterations: Higher is more secure but slower. Start high (e.g., 260000+)
# Adjust based on your server performance and security needs.
# OWASP recommendation (as of late 2023) is 600,000 for PBKDF2-HMAC-SHA256
ITERATIONS = 390000 # Example value, tune as needed
SALT_BYTES = 16     # Size of the salt (16 bytes is common)
DK_LENGTH = 32      # Desired key length in bytes (e.g., 32 for SHA256)

# --- Helper Functions for Hashing ---

def hash_password(password):
    """Hashes a password using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(SALT_BYTES)
    # Password must be bytes
    pwd_bytes = password.encode('utf-8')
    # Calculate the hash
    key = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        pwd_bytes,
        salt,
        ITERATIONS,
        dklen=DK_LENGTH
    )
    # Store salt and key as hex strings for easier storage
    salt_hex = binascii.hexlify(salt).decode('ascii')
    key_hex = binascii.hexlify(key).decode('ascii')
    # Return in 'salt:key' format
    return f"{salt_hex}:{key_hex}"

def verify_password(stored_password_info, provided_password):
    """Verifies a provided password against the stored salt and hash."""
    if not stored_password_info or ':' not in stored_password_info:
        print("Error: Invalid or missing stored password info.")
        return False
    try:
        salt_hex, key_hex = stored_password_info.split(':')
        salt = binascii.unhexlify(salt_hex)
        stored_key = binascii.unhexlify(key_hex)
    except (ValueError, binascii.Error):
        # Invalid format or hex decoding failed
        print(f"Error: Invalid stored password format for hash starting with '{salt_hex[:8]}...'")
        return False

    # Password must be bytes
    provided_pwd_bytes = provided_password.encode('utf-8')

    # Calculate the hash for the provided password using the stored salt
    new_key = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        provided_pwd_bytes,
        salt,
        ITERATIONS,
        dklen=DK_LENGTH
    )

    # Compare the derived key with the stored key
    # hmac.compare_digest helps prevent timing attacks
    return hmac.compare_digest(stored_key, new_key)

# --- User Credentials Store (Loaded from logins.sql) --- <--- MODIFIED
# This dictionary will be populated by load_user_data_from_sql()
user_password_store = {}
# --- End User Credentials Store ---

# --- Session Configuration ---
SESSION_COOKIE_NAME = "ColorDaysSession"
VALID_SESSION_VALUE = "user_is_logged_in_secret_value" # Replace with a secure, random session ID mechanism
# --- End Session Configuration ---


# --- In-Memory Data Store and Lock ---
data_store = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
data_lock = threading.RLock()


# --- SQL File Handling Functions ---

# --- Parsing for tables.sql ---
def parse_sql_line(line):
    """Parses a single INSERT statement line for the counts table."""
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
            print(f"Warning: Could not parse numbers in counts line: {line.strip()}")
            return None
    else:
        # Ignore comments and empty lines silently
        if line.strip() and not line.strip().startswith('--') and not line.strip().upper().startswith('CREATE TABLE'):
             print(f"Warning: Could not parse counts line format: {line.strip()}")
        return None

# --- Parsing for logins.sql --- <--- NEW
def parse_logins_sql_line(line):
    """Parses a single valid INSERT line for the users table."""
    line = line.strip()

    # Skip empty lines or comments
    if not line or line.startswith('--'):
        return None

    # Must start with an actual INSERT line
    if not line.upper().startswith("INSERT INTO USERS"):
        return None

    # Regex to extract username and password_hash
    match = re.match(
        r"INSERT INTO users\s*\(\s*username\s*,\s*password_hash\s*\)\s*VALUES\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\);",
        line,
        re.IGNORECASE
    )

    if match:
        username, password_hash = match.groups()
        if ':' in password_hash:
            return username, password_hash
        else:
            print(f"Warning: Skipped user due to bad hash format: {line}")
            return None
    else:
        print(f"Warning: Could not parse logins line format: {line}")
        return None

# --- Loading for tables.sql ---
def load_data_from_sql():
    """Loads data from tables.sql into the in-memory data_store."""
    global data_store
    print(f"Attempting to load counts data from: {SQL_FILE_PATH}")
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
                             print(f"Warning: Invalid data values skipped in counts line {line_num}: {line.strip()}")

            print(f"Loaded counts data for classes found in file: {', '.join(sorted(list(found_classes)))}")

        except Exception as e:
            print(f"!!! ERROR reading or parsing {SQL_FILE_PATH}: {e}. Counts data store might be empty or incomplete.")
            # Optionally clear temp_data if error is severe
            # temp_data.clear()
            # found_classes.clear()

    else:
         print(f"Warning: {SQL_FILE_PATH} not found. Will initialize default counts data.")

    # Ensure all SUPPORTED_CLASSES have default entries if missing
    needs_save = False
    for class_name in SUPPORTED_CLASSES:
        if class_name not in temp_data: # Check against temp_data, not found_classes
             print(f"Initializing default zero counts data for missing class: {class_name}")
             needs_save = True # Need to save the defaults we're adding
             for type_val in ['student', 'teacher']:
                 for points_val in range(7): # 0 to 6
                     temp_data[class_name][type_val][points_val] = 0 # Default to 0

    # Update the global data store under lock
    with data_lock:
        data_store = temp_data

    # If we added defaults or the file didn't exist, save the current state
    if needs_save or not file_exists:
        print("Saving initial/default counts data state to tables.sql...")
        # This call will acquire the RLock again, which is allowed
        if not save_data_to_sql():
             print("!!! CRITICAL: Failed to save initial counts data. File might be missing or unwritable.")

    print("Counts data loading/initialization complete.")

# --- Loading for logins.sql --- <--- NEW
def load_user_data_from_sql():
    """Loads user data from logins.sql into the in-memory user_password_store."""
    global user_password_store
    print(f"Attempting to load user data from: {LOGINS_SQL_FILE_PATH}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp_user_store = {}
    file_exists = LOGINS_SQL_FILE_PATH.exists()
    users_loaded_count = 0

    if file_exists:
        try:
            with open(LOGINS_SQL_FILE_PATH, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    parsed = parse_logins_sql_line(line)
                    if parsed:
                        username, password_hash = parsed
                        temp_user_store[username] = password_hash
                        users_loaded_count += 1

            print(f"Loaded {users_loaded_count} user(s) from {LOGINS_SQL_FILE_PATH}.")

        except Exception as e:
            print(f"!!! ERROR reading or parsing {LOGINS_SQL_FILE_PATH}: {e}. User data store might be empty or incomplete.")
            temp_user_store.clear()

    else:
        print(f"Warning: {LOGINS_SQL_FILE_PATH} not found. No users loaded. Login will not work.")

    user_password_store = temp_user_store

    if users_loaded_count == 0:
        print("!!! WARNING: No user accounts loaded. Login functionality will be unavailable.")
        print(f"!!! Ensure {LOGINS_SQL_FILE_PATH} exists, is readable, and contains valid INSERT statements.")
        print(f"!!! Example INSERT: INSERT INTO users (username, password_hash) VALUES ('admin', '{hash_password('password123')}');")

    print("User data loading complete.")


# --- Saving for tables.sql ---
def save_data_to_sql():
    """Saves the current in-memory data_store back to tables.sql. Returns True on success, False on failure."""
    global data_store
    print(f"Attempting to save counts data to: {SQL_FILE_PATH}")
    # Acquire lock. RLock allows acquiring again if the thread already holds it.
    with data_lock:
        try:
            sql_lines = []
            sql_lines.append(f"-- Data saved on {datetime.datetime.now().isoformat()} --")
            sql_lines.append("-- This file is used as the primary data storage for counts. --")
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
            print(f"Counts data successfully saved to {SQL_FILE_PATH}") # Success message
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

    # (Helper methods: get_cookies, is_logged_in, _send_response remain the same)
    def get_cookies(self):
        cookies = SimpleCookie()
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            cookies.load(cookie_header)
        return cookies

    # Helper to check if user is logged in based on session cookie
    def is_logged_in(self):
        cookies = self.get_cookies()
        session_cookie = cookies.get(SESSION_COOKIE_NAME)
        if session_cookie and session_cookie.value == VALID_SESSION_VALUE:
            return True
        return False

    # Helper to send JSON responses with CORS headers
    def _send_response(self, status_code, data=None, content_type='application/json', headers=None):
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

    # (do_GET remains largely the same - including login redirect logic)
    def do_GET(self):
        global data_store # Keep access to counts data
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
                        for points_val in range(7):
                            count = class_data.get(type_val, {}).get(points_val, 0)
                            response_data.append({"type": type_val, "points": points_val, "count": count})
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
        global data_store # Keep access to counts data
        global user_password_store # Access loaded user data <--- NEW
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        # Allow empty body for /logout
        if content_length == 0 and path != '/logout':
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
                # --- MODIFIED: Look up user in the loaded store ---
                stored_info = user_password_store.get(username)
                # --- END MODIFICATION ---

                # Check if user exists and password was provided
                if stored_info and submitted_password:
                    # Verify the password using the stored salt and hash info
                    if verify_password(stored_info, submitted_password):
                        login_successful = True
                    else:
                        print(f"Password verification failed for user: {username}") # Added detail
                elif not stored_info:
                     print(f"Login attempt failed: Username '{username}' not found.")
                elif not submitted_password:
                     print(f"Login attempt failed: No password provided for user '{username}'.")


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
                    # Generic error message to client, specific logs server-side
                    self._send_response(401, {"error": "Invalid username or password"}) # Unauthorized

            except json.JSONDecodeError:
                 print("Error: Invalid JSON received for login.")
                 self._send_response(400, {"error": "Invalid JSON format in request body"})
            except Exception as e:
                print(f"Error during login processing: {e}")
                print(traceback.format_exc())
                self._send_response(500, {"error": f"Server error during login"})
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

        # --- Handle /api/increment ---
        if path == '/api/increment':
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

            success = False
            message = "Increment failed"
            status_code = 500
            save_needed = False

            with data_lock:
                try:
                    current_count = data_store.get(class_name, {}).get(type_val, {}).get(points_val, 0)
                    data_store[class_name][type_val][points_val] = current_count + 1
                    save_needed = True

                    if save_needed:
                        print(f"DEBUG: Change detected (increment), attempting save...")
                        if save_data_to_sql():
                            success = True
                            message = "Count incremented"
                            status_code = 200
                        else:
                            success = False
                            message = "Count incremented in memory, but CRITICAL error saving to file."
                            status_code = 500
                except Exception as e:
                    print(f"!!! UNEXPECTED ERROR during POST {path} operation (within lock):")
                    print(traceback.format_exc())
                    success = False
                    message = "An internal error occurred during the increment operation."
                    status_code = 500

            if status_code == 200:
                 self._send_response(status_code, {"success": success, "message": message})
            else:
                 self._send_response(status_code, {"error": message})
            return # Handled

        # --- Handle /api/decrement ---
        elif path == '/api/decrement':
            class_name = data.get('className')
            type_val = data.get('type')
            points_val = data.get('points')

            # Basic validation (repeated for clarity, could be refactored)
            if not all([class_name, type_val, points_val is not None]):
                self._send_response(400, {"error": "Missing data: className, type, or points"})
                return
            if type_val not in ['student', 'teacher']:
                self._send_response(400, {"error": "Invalid type"})
                return
            if not isinstance(points_val, int) or not (0 <= points_val <= 6):
                 self._send_response(400, {"error": "Invalid points value"})
                 return

            success = False
            message = "Decrement failed"
            status_code = 500
            save_needed = False

            with data_lock:
                try:
                    current_count = data_store.get(class_name, {}).get(type_val, {}).get(points_val, 0)
                    if current_count > 0:
                        data_store[class_name][type_val][points_val] = current_count - 1
                        save_needed = True
                    else:
                        success = False # Operation didn't change state
                        message = "Count already zero"
                        status_code = 400 # Bad Request
                        save_needed = False # No change, no save needed

                    if save_needed:
                        print(f"DEBUG: Change detected (decrement), attempting save...")
                        if save_data_to_sql():
                            success = True
                            message = "Count decremented"
                            status_code = 200
                        else:
                            success = False
                            message = "Count decremented in memory, but CRITICAL error saving to file."
                            status_code = 500
                except Exception as e:
                    print(f"!!! UNEXPECTED ERROR during POST {path} operation (within lock):")
                    print(traceback.format_exc())
                    success = False
                    message = "An internal error occurred during the decrement operation."
                    status_code = 500

            if status_code == 200:
                 self._send_response(status_code, {"success": success, "message": message})
            else:
                 self._send_response(status_code, {"error": message})
            return # Handled

        # --- Handle unknown authenticated POST paths ---
        else:
            print(f"Authenticated POST request to unknown path: {path}")
            self._send_response(404, {"error": "API endpoint not found"})


# --- Main Execution ---
if __name__ == "__main__":
    print("--- Starting Color Days Server ---")

    # --- Load Data ---
    # Load counts data first
    load_data_from_sql()
    # Load user login data <--- NEW
    load_user_data_from_sql()
    # --- End Load Data ---

    # Server setup using ThreadingMixIn for basic concurrency
    class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True # Allow shutdown even if threads are running
        allow_reuse_address = True # Allow quick restarts

    httpd = ThreadingHTTPServer((HOST, PORT), ColorDaysHandler)

    print(f"\nServing HTTP on {HOST}:{PORT}...")
    print(f"Frontend root: {FRONTEND_DIR}")
    print(f"Using counts data file: {SQL_FILE_PATH}")
    print(f"Using logins data file: {LOGINS_SQL_FILE_PATH}") # <--- NEW
    print(f"Using hashlib.pbkdf2_hmac with {ITERATIONS} iterations.")
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

