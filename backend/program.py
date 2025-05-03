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

def verify_password(stored_password_info, provided_password, username):
    """Verifies a provided password against the stored salt and hash."""
    extra_cookie_headers = [] # Initialize default empty list

    if not stored_password_info or ':' not in stored_password_info:
        # Check for pre-generated password format _password_
        if stored_password_info and stored_password_info.startswith('_') and stored_password_info.endswith('_'):
            _stored_password_info_ = stored_password_info[1:-1]
            if _stored_password_info_ == provided_password:
                print(f"User '{username}' logged in with pregenerated password '{provided_password}'. Setting change password cookie.")
                # Create the specific cookie needed for this case
                change_pw_cookie_headers = create_cookies(
                    CHANGE_PASSWORD_COOKIE_NAME,
                    "not-required", # Use a simple value like "required" or "true"
                    path='/', # Apply cookie to root path so it's sent for all requests
                    max_age=3600 # Optional: Give it a lifetime (e.g., 1 hour)
                )
                return True, change_pw_cookie_headers # Return True and the specific cookie headers
            else:
                # Pregenerated password provided, but it didn't match
                print(f"Pregenerated password verification failed for user: {username}")
                return False, [] # <-- MODIFIED: Return tuple
        else:
            # Stored info is invalid (not pregenerated format and no ':')
            print(f"Error: Invalid or missing stored password info for user '{username}'.")
            return False, [] # <-- MODIFIED: Return tuple
    try:
        salt_hex, key_hex = stored_password_info.split(':')
        salt = binascii.unhexlify(salt_hex)
        stored_key = binascii.unhexlify(key_hex)
    except (ValueError, binascii.Error):
        # Invalid format or hex decoding failed
        print(f"Error: Invalid stored password format for hash starting with '{salt_hex[:8]}...' for user '{username}'")
        return False, [] # <-- MODIFIED: Return tuple

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
    is_match = hmac.compare_digest(stored_key, new_key)
    return is_match, [] # <-- MODIFIED: Return tuple (True/False, empty list)

# --- User Credentials Store (Loaded from logins.sql) --- <--- MODIFIED
# This dictionary will be populated by load_user_data_from_sql()
user_password_store = {}
# --- End User Credentials Store ---

# --- Session Configuration ---
USERNAME_COOKIE_NAME = "ColorDaysUser"
SESSION_COOKIE_NAME = "ColorDaysSession"
VALID_SESSION_VALUE = "user_is_logged_in_secret_value" # Replace with a secure, random session ID mechanism
CHANGE_PASSWORD_COOKIE_NAME = "ChangePasswordVerificationNotNeeded" # For the change password flow
# --- End Session Configuration ---


# --- In-Memory Data Store and Lock ---
data_store = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
data_lock = threading.RLock()

def create_cookies(name, value, path='/', expires=None, max_age=None, httponly=True, samesite='Lax'):
    """
    Creates a list of ('Set-Cookie', header_value) tuples for a single cookie.

    Args:
        name (str): The name of the cookie.
        value (str): The value of the cookie.
        path (str, optional): The path for the cookie. Defaults to '/'.
        expires (str, optional): GMT expiration string (e.g., 'Thu, 01 Jan 1970 00:00:00 GMT'). Defaults to None.
        max_age (int, optional): Max age in seconds. Defaults to None.
        httponly (bool, optional): Set the HttpOnly flag. Defaults to True.
        samesite (str, optional): Set the SameSite attribute ('Lax', 'Strict', 'None'). Defaults to 'Lax'.

    Returns:
        list: A list containing one tuple: ('Set-Cookie', formatted_header_string).
              Returns an empty list if name or value is empty/None.
    """
    if not name or value is None: # Basic validation
        print(f"Warning: Attempted to create cookie with empty name ('{name}') or None value.")
        return []

    cookie = SimpleCookie()
    cookie[name] = value
    cookie[name]['path'] = path

    # Add security and lifetime attributes if specified
    if httponly:
        cookie[name]['httponly'] = True
    if samesite:
        cookie[name]['samesite'] = samesite
    if expires:
        cookie[name]['expires'] = expires
    if max_age is not None: # Check for None explicitly as 0 is valid
        cookie[name]['max-age'] = max_age

    headers = []
    # There will only be one morsel since we created one cookie
    for morsel in cookie.values():
        # morsel.output(header='') gives the value part like 'key=val; path=/; httponly...'
        header_value = morsel.output(header='').strip()
        headers.append(('Set-Cookie', header_value)) # Append the tuple

    return headers

def create_cookie_clear_headers(name, path='/'):
    """
    Creates a list of ('Set-Cookie', header_value) tuples to clear a cookie.

    Args:
        name (str): The name of the cookie to clear.
        path (str, optional): The path of the cookie (must match original). Defaults to '/'.

    Returns:
        list: A list containing one tuple: ('Set-Cookie', formatted_header_string).
              Returns an empty list if name is empty/None.
    """
    if not name:
        print("Warning: Attempted to clear cookie with empty name.")
        return []

    cookie = SimpleCookie()
    cookie[name] = "" # Clear value
    cookie[name]['path'] = path
    cookie[name]['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT' # Expire immediately
    cookie[name]['max-age'] = 0 # Another way to expire

    # Generate the header string
    header_value = cookie[name].output(header='').strip()
    return [('Set-Cookie', header_value)] # Return as a list of tuples


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
        if ':' in password_hash or password_hash.upper() == '_NULL_' or (password_hash[0] == '_' and password_hash[-1] == '_'):
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
    return user_password_store # Return the loaded user_password_store for use in the handler


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
        
# --- Add this function near save_data_to_sql ---

# --- Lock for user data modifications ---
# It's better practice to have a separate lock for user data
# if it might be modified concurrently with counts data,
# but for simplicity here, we'll reuse data_lock.
# Consider adding user_data_lock = threading.RLock() if needed.

def save_user_data_to_sql():
    """Saves the current user_password_store back to logins.sql. Returns True on success, False on failure."""
    global user_password_store
    print(f"Attempting to save user data to: {LOGINS_SQL_FILE_PATH}")
    # Use the same lock as counts for simplicity, or create a dedicated one
    with data_lock: # Or use a dedicated user_data_lock
        try:
            sql_lines = []
            sql_lines.append(f"-- User data saved on {datetime.datetime.now().isoformat()} --")
            # Optional: Add back the CREATE TABLE comment if you want it preserved
            # sql_lines.append("-- CREATE TABLE IF NOT EXISTS users (...)")
            sql_lines.append("")

            # Iterate through the in-memory store and generate INSERT statements
            # Sort by username for consistent file output
            for username, password_hash in sorted(user_password_store.items()):
                 # Basic escaping for username (should be sufficient if usernames don't contain quotes)
                 safe_username = username.replace("'", "''")
                 # Password hash is already hex, should be safe
                 insert_statement = f"INSERT INTO users (username, password_hash) VALUES ('{safe_username}', '{password_hash}');"
                 sql_lines.append(insert_statement)

            # Write the file (overwrite existing)
            with open(LOGINS_SQL_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write("\n".join(sql_lines))
                f.write("\n") # Add a final newline
            print(f"User data successfully saved to {LOGINS_SQL_FILE_PATH}")
            return True

        except PermissionError as e:
            print(f"!!! PERMISSION ERROR writing to {LOGINS_SQL_FILE_PATH}: {e}")
            return False
        except IOError as e:
            print(f"!!! IO ERROR writing to {LOGINS_SQL_FILE_PATH}: {e}")
            return False
        except Exception as e:
            print(f"!!! UNEXPECTED ERROR during save_user_data_to_sql:")
            print(traceback.format_exc())
            return False

# --- End of new function ---

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

    def send_json(self, data, status=200):
        response = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    # Handle CORS preflight requests
    def do_OPTIONS(self):
        self._send_response(204) # No Content for OPTIONS

    # Inside your request handler (e.g., in do_GET or do_POST):

    def handle_get_users(self):
        users = load_user_data_from_sql() # <--- Corrected line (no argument)
        user_list = []
        for username, password_hash in users.items():
            # Determine status based on the hash format from the file
            if password_hash is None or password_hash.upper() == '_NULL_': # Check for NULL explicitly if handle_add_user writes it
                status = "not_set"
            # You might need a more robust check than just length if handle_add_user writes NULL
            # Let's assume parse_logins_sql_line filters out bad hashes, so what's loaded is valid or None/NULL
            elif password_hash[0] == '_' and password_hash[-1] == '_':
                status = password_hash[1:-1] # Extract the password between underscores
            else:
                status = "set" # If it has a valid hash format, it's set

            # The frontend expects 'password' field, map status to it
            user_list.append({"username": username, "password": status})
        self.send_json(user_list)

    def handle_post_users(self):
        global user_password_store

        if not self.is_logged_in():
            print("Denied POST to /api/users - not authenticated.")
            self._send_response(401, {"error": "Authentication required"})
            return

        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._send_response(400, {"error": "Missing request body"})
            return

        try:
            post_data = json.loads(self.rfile.read(content_length))
            username = post_data.get("username", "").strip()

            if not username:
                self._send_response(400, {"error": "Username required"})
                return

            if username in user_password_store:
                self._send_response(400, {"error": "User already exists"})
                return

            # Add the user with NOT_SET as the password
            user_password_store[username] = "NOT_SET"

            # Call your save function here!
            success = save_user_data_to_sql()

            if success:
                print(f"User '{username}' added and saved.")
                self._send_response(200, {"message": "User added"})
            else:
                self._send_response(500, {"error": "Failed to save user data"})

        except Exception as e:
            print(f"Error in handle_post_users: {e}")
            traceback.print_exc()
            self._send_response(500, {"error": "Failed to process request"})

    def handle_add_user(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        print("Raw body:", repr(body))

        if not body:
            self.send_error(400, "Missing request body")
            return

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        username = data.get("username")
        if not username:
            self.send_error(400, "Missing username")
            return

        users = load_user_data_from_sql(LOGINS_SQL_FILE_PATH)
        if username in users:
            self.send_error(409, "User already exists")
            return

        with open(LOGINS_SQL_FILE_PATH, 'a') as f:
            f.write(f"INSERT INTO users (username, password_hash) VALUES ('{username}', NULL);\n")

        self.send_response(200)
        self.end_headers()

    def handle_remove_user(self, data): # Accept parsed data
        username = data.get("username")

        if not username:
            self._send_response(400, {"error": "Missing username"})
            return

        # --- Prevent deleting admin user ---
        if username == 'admin':
            print("Attempt denied to remove 'admin' user.")
            self._send_response(403, {"error": "Cannot remove the admin user."}) # Forbidden
            return
        # --- End admin check ---

        success = False
        message = "Failed to remove user."
        status_code = 500
        save_needed = False

        with data_lock: # Use the lock
            if username not in user_password_store:
                message = f"User '{username}' not found."
                status_code = 404 # Not Found
            else:
                del user_password_store[username] # Remove from memory
                save_needed = True
                print(f"User '{username}' removed from memory.")

            if save_needed:
                if save_user_data_to_sql(): # Save changes
                    success = True
                    message = f"User '{username}' removed successfully."
                    status_code = 200 # OK
                else:
                    # CRITICAL: Failed to save. User removed from memory but not file.
                    # Consider reloading user data from file or other recovery.
                    success = False
                    message = f"User '{username}' removed from memory, but FAILED to save to file."
                    status_code = 500

        if success:
            self._send_response(status_code, {"success": True, "message": message})
        else:
            self._send_response(status_code, {"error": message})

    def handle_reset_password(self, data): # Accept parsed data
        username = data.get("username")
        new_password = data.get("new_password")

        # --- Add checks for missing data ---
        if not username or not new_password:
            print("Error: Missing username or new_password in handle_reset_password data.")
            self._send_response(400, {"error": "Missing username or new_password"})
            return
        # --- End checks ---

        hashed = f"_{new_password}_"

        # --- IMPORTANT: Use the in-memory store and save function ---
        # This file manipulation logic is prone to errors and bypasses locking/memory store.
        # Replace the file reading/writing block with the correct logic:

        success = False
        message = "Failed to set password."
        status_code = 500
        save_needed = False

        with data_lock: # Use the lock
            if username not in user_password_store:
                message = f"User '{username}' not found."
                status_code = 404 # Not Found
            else:
                try:
                    # Update the in-memory store
                    user_password_store[username] = hashed
                    save_needed = True
                    print(f"Password set/reset in memory for user '{username}'.")
                except Exception as e:
                    print(f"!!! Error hashing new password for {username}: {e}")
                    message = "Server error during password hashing."
                    status_code = 500

            if save_needed:
                # Call the proper save function
                if save_user_data_to_sql():
                    success = True
                    message = f"Password for user '{username}' set/reset successfully."
                    status_code = 200 # OK
                else:
                    success = False
                    # User store might be inconsistent if save fails!
                    message = f"Password set/reset in memory for '{username}', but FAILED to save to file."
                    status_code = 500

        if success:
            self._send_response(status_code, {"success": True, "message": message})
        else:
            self._send_response(status_code, {"error": message})

# --- Inside the ColorDaysHandler class ---

    def do_GET(self):
        global data_store
        global user_password_store # Add access to user store
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)

        if path == '/list_users':
            # --- Authentication Check ---
            if not self.is_logged_in():
                print(f"Denied GET request to {path} - User not logged in.")
                self._send_response(401, {"error": "Authentication required"})
                return
            # --- End Authentication Check ---

            # Acquire lock briefly to read user list safely
            with data_lock: # Or use a dedicated user_data_lock
                # Return only the usernames (keys of the dictionary)
                user_list = sorted(list(user_password_store.keys()))

            print(f"Authenticated request for user list. Sending {len(user_list)} users.")
            self._send_response(200, user_list)
            return
        # --- END NEW ENDPOINT ---

        # --- Password Change Check (for API endpoints in GET) ---
        # Apply this check before specific API handlers if they shouldn't run during forced change
        # Must happen *after* login check but *before* executing the endpoint logic
        is_logged_in_flag = self.is_logged_in() # Check login status once
        cookies = self.get_cookies() # Get cookies once
        password_change_required = cookies.get(CHANGE_PASSWORD_COOKIE_NAME)

        # Define paths allowed even if password change is required
        # Note: GET requests usually serve pages or read data. API GETs are less common but possible.
        allowed_get_paths_during_change = ['/login.html', '/change-password.html', '/logout']
        # Add essential CSS/JS if needed for change-password.html
        # allowed_get_paths_during_change.append('/style.css')

        # Block API GET requests if change is required (adjust allowed paths if needed)
        if is_logged_in_flag and password_change_required and path.startswith('/api/') and path not in allowed_get_paths_during_change:
            print(f"Denied GET request to API {path} - Password change required.")
            # For API endpoints, sending an error is usually better than redirecting
            self._send_response(403, {"error": "Password change required before accessing this API resource."})
            return
        # --- End Password Change Check for API GET ---

        elif path == '/api/users':
            # Note: handle_get_users currently doesn't check authentication
            # Add authentication check here if needed:
            # if not self.is_logged_in():
            #     print(f"Denied GET request to {path} - User not logged in.")
            #     self._send_response(401, {"error": "Authentication required"})
            #     return
            print(f"Handling GET request for {path}") # Add log
            self.handle_get_users() # Call the handler function
            return # Make sure to return after handling

        # API Endpoint: /api/counts?class=ClassName
        elif path == '/api/counts':
            # ... (existing code for /api/counts remains the same)
            # ... make sure it also has an authentication check if needed!
            # --- Authentication Check (Example - Add if counts should be protected) ---
            # if not self.is_logged_in():
            #     print(f"Denied GET request to {path} - User not logged in.")
            #     self._send_response(401, {"error": "Authentication required"})
            #     return
            # --- End Authentication Check ---
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
            return # Make sure to return after handling

        # File Serving Logic
        # --- Password Change Check (for Pages) ---
        # Check *after* login check but *before* serving protected files
        # Use flags checked earlier (is_logged_in_flag, password_change_required)

        if is_logged_in_flag and password_change_required and path not in allowed_get_paths_during_change and not path.startswith('/api/'): # Don't redirect API calls here
            print(f"Redirecting GET request for {path} to /change-password.html - Password change required.")
            self.send_response(302) # Found (redirect)
            self.send_header('Location', '/change-password.html')
            self.end_headers()
            return
        # --- End Password Change Check for Pages ---
        try:
            # Default to menu.html if root path is requested
            # Check for login.html request specifically
            if path == '/login.html':
                file_path = FRONTEND_DIR / 'login.html'
            elif path == '/':
                # Redirect root to login page if not logged in, else menu
                if is_logged_in_flag: # Use the flag checked earlier
                    file_path = FRONTEND_DIR / 'menu.html'
                else:
                    # Send redirect header
                    self.send_response(302) # Found (redirect)
                    self.send_header('Location', '/login.html')
                    self.end_headers()
                    return # Stop processing further
            elif path == '/change-password.html': # Serve the new page
                file_path = FRONTEND_DIR / 'change-password.html'
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
        global user_password_store # Already accessed here
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

                # Initialize login result and extra headers
                login_successful = False
                extra_cookie_headers = [] # <-- Initialize empty list

                stored_info = user_password_store.get(username)

                if stored_info and submitted_password:
                    # --- UNPACK the tuple returned by verify_password ---
                    login_successful, extra_cookie_headers = verify_password(stored_info, submitted_password, username)
                    # --- END CHANGE ---
                    if not login_successful:
                        print(f"Password verification failed for user: {username}")
                elif not stored_info:
                    print(f"Login attempt failed: Username '{username}' not found.")
                elif not submitted_password:
                    print(f"Login attempt failed: No password provided for user '{username}'.")


                if login_successful:
                    # --- Prepare the standard cookies ---
                    user_cookie_headers = create_cookies(USERNAME_COOKIE_NAME, f"{username}", path='/')
                    session_cookie_headers = create_cookies(SESSION_COOKIE_NAME, f"{VALID_SESSION_VALUE}", path='/')

                    # --- COMBINE standard cookies with any extra ones returned ---
                    all_cookie_headers = user_cookie_headers + session_cookie_headers + extra_cookie_headers
                    # --- END CHANGE ---

                    # --- Send response headers MANUALLY ---
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    # CORS Headers...
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
                    self.send_header('Access-Control-Allow-Credentials', 'true')

                    # Send EACH Set-Cookie header individually
                    print(f"DEBUG: Preparing to send {len(all_cookie_headers)} cookie(s)...")
                    for header_name, header_value in all_cookie_headers:
                        self.send_header(header_name, header_value)
                        print(f"DEBUG: Sent {header_name} header: {header_value}")

                    self.end_headers()

                    response_body = json.dumps({"success": True, "message": "Login successful"}).encode('utf-8')
                    self.wfile.write(response_body)

                    print(f"Login successful for user: {username}, {len(all_cookie_headers)} session/other cookie(s) sent.")

                else: # login_successful == False
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
            print("Logout request received. Preparing cookie clearing headers.")
            # Prepare expired cookies to clear the browser's cookies

            # --- Use the new function to get clearing headers ---
            session_clear_headers = create_cookie_clear_headers(SESSION_COOKIE_NAME, path='/')
            user_clear_headers = create_cookie_clear_headers(USERNAME_COOKIE_NAME, path='/')
            change_pw_clear_headers = create_cookie_clear_headers(CHANGE_PASSWORD_COOKIE_NAME, path='/') # Clear this too
            all_clear_headers = session_clear_headers + user_clear_headers + change_pw_clear_headers
            # --- End using new function ---

            # --- Send response headers MANUALLY ---
            # Use the same technique as login to ensure both headers are sent
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            # --- CORS Headers (copy from _send_response/login) ---
            self.send_header('Access-Control-Allow-Origin', '*') # Consider restricting in production
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
            self.send_header('Access-Control-Allow-Credentials', 'true')
            # --- End CORS ---

            # --- Send EACH Set-Cookie expiration header individually ---
            print(f"DEBUG: Preparing to send {len(all_clear_headers)} cookie clearing header(s)...")
            for header_name, header_value in all_clear_headers:
                self.send_header(header_name, header_value)
                print(f"DEBUG: Sent Set-Cookie expiration header: {header_value}")

            self.end_headers() # Crucial: End headers AFTER all headers are sent

            # Send the response body
            response_body = json.dumps({"success": True, "message": "Logged out successfully"}).encode('utf-8')
            self.wfile.write(response_body)

            print("Logout successful, cookie expiration headers sent.")
            return # Stop processing after handling /logout
        # --- End Authentication Check ---

        # --- Password Change Check for POST ---
        # Must happen *after* login check but *before* executing protected endpoint logic
        cookies = self.get_cookies() # Get fresh cookies for POST check
        password_change_required = cookies.get(CHANGE_PASSWORD_COOKIE_NAME)

        # Define allowed POST paths during forced change
        allowed_post_paths_during_change = ['/login', '/logout', '/api/auth/change']

        if password_change_required and path not in allowed_post_paths_during_change:
            print(f"Denied POST request to {path} - Password change required.")
            self._send_response(403, {"error": "Password change required before performing this action."})
            return
        # --- End Password Change Check ---

        # --- Protected Endpoints below require login ---
        print(f"Processing authenticated POST request to {path}...") # Log access

        # Parse JSON body (already read, just need to decode)
        try:
            # Handle potential empty body for endpoints that might not need it (though ours do)
            if content_length > 0:
                data = json.loads(body)
            else:
                data = {} # Or handle error if body is required
        except json.JSONDecodeError:
            self._send_response(400, {"error": "Invalid JSON payload"})
            return

        # --- Handle /add_user ---
        if path == '/add_user':
            username = data.get('username')
            password = data.get('password')

            if not username:
                self._send_response(400, {"error": "Missing username"})
                return
            
            if not password:
                pass_null = True
            else:
                pass_null = False

            success = False
            message = "Failed to add user."
            status_code = 500
            save_needed = False

            with data_lock: # Or use a dedicated user_data_lock
                if username in user_password_store:
                    message = f"Username '{username}' already exists."
                    status_code = 409 # Conflict
                else:
                    if pass_null == False:
                        try:
                            hashed_pw = hash_password(password)
                            user_password_store[username] = hashed_pw
                            save_needed = True
                            print(f"User '{username}' added to memory.")
                        except Exception as e:
                            print(f"!!! Error hashing password for {username}: {e}")
                            message = "Server error during password hashing."
                            status_code = 500
                    else:
                        hashed_pw = "_NULL_" # Explicitly set to null
                        user_password_store[username] = hashed_pw
                        print(f"User '{username}' added to memory with NULL password.")
                        save_needed = True

                if save_needed:
                    if save_user_data_to_sql():
                        success = True
                        message = f"User '{username}' added successfully."
                        status_code = 201 # Created
                    else:
                        # CRITICAL: Failed to save, potentially revert memory change?
                        # For simplicity, we'll report the save error but leave memory changed.
                        # Consider removing the user from memory here if atomicity is crucial.
                        # del user_password_store[username]
                        success = False
                        message = f"User '{username}' added to memory, but FAILED to save to file."
                        status_code = 500

            if success:
                 self._send_response(status_code, {"success": True, "message": message})
            else:
                 self._send_response(status_code, {"error": message}) # Send error message for frontend alert
            return # Handled

        # --- Handle /change_password ---
        elif path == '/api/auth/change':
            # --- CORRECTED USERNAME RETRIEVAL ---
            username_cookie = self.get_cookies().get(USERNAME_COOKIE_NAME)
            if username_cookie:
                username = username_cookie.value # Extract the string value from the Morsel
            else:
                # This case should ideally not happen if the request is authenticated,
                # but handle it defensively.
                print("Error: Username cookie missing in authenticated /api/auth/change request.")
                self._send_response(401, {"error": "Authentication error: User identity not found."})
                return
            # --- END CORRECTION ---

            old_password = data.get('oldPassword')
            new_password = data.get('newPassword') # Get new password from request

            # --- Check for the cookie and force verification if present ---
            cookies = self.get_cookies()
            if cookies.get(CHANGE_PASSWORD_COOKIE_NAME):
                print(f"DEBUG: Cookie '{CHANGE_PASSWORD_COOKIE_NAME}' found. Forcing verification_needed to False.")
                verification_needed = False # Override whatever the client sent
            # --- End cookie check ---
            
            if not username or not new_password:
                self._send_response(400, {"error": "Missing username or new password"})
                return

            success = False
            message = "Failed to change password."
            status_code = 500
            save_needed = False

            with data_lock: # Or use a dedicated user_data_lock
                stored_password_info = user_password_store.get(username)

                if not stored_password_info:
                    message = f"User '{username}' not found."
                    status_code = 404 # Not Found
                else:
                    if verification_needed == True:
                        # verify_password returns a tuple (bool, headers)
                        is_old_valid, _ = verify_password(stored_password_info, old_password, username)
                        if not is_old_valid:
                        # if verify_password(stored_password_info, old_password, username) == False:
                            message = "Old password verification failed."
                            status_code = 401
                            self._send_response(status_code, {"error": message})
                            return

                    try:
                        hashed_pw = hash_password(new_password)
                        user_password_store[username] = hashed_pw
                        save_needed = True
                        print(f"Password changed in memory for user '{username}'.")
                    except Exception as e:
                        print(f"!!! Error hashing new password for {username}: {e}")
                        message = "Server error during password hashing."
                        status_code = 500

                if save_needed:
                    if save_user_data_to_sql():
                        success = True
                        message = f"Password for user '{username}' changed successfully."
                        status_code = 200 # OK
                    else:
                        success = False
                        message = f"Password changed in memory for '{username}', but FAILED to save to file."
                        status_code = 500

            if success:
                # --- Clear the change password cookie if it exists ---
                extra_headers_on_success = []
                cookies = self.get_cookies() # Check cookies again just before sending response
                if cookies.get(CHANGE_PASSWORD_COOKIE_NAME):
                    print(f"DEBUG: Password change successful, clearing '{CHANGE_PASSWORD_COOKIE_NAME}' cookie.")
                    clear_headers = create_cookie_clear_headers(CHANGE_PASSWORD_COOKIE_NAME, path='/')
                    extra_headers_on_success.extend(clear_headers)
                # --- End cookie clearing ---

                # --- Send response headers MANUALLY to include potential cookie clearing ---
                self.send_response(status_code) # Should be 200
                self.send_header('Content-type', 'application/json')
                # CORS Headers (copy from _send_response or login)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
                self.send_header('Access-Control-Allow-Credentials', 'true')
                # Send extra headers (e.g., Set-Cookie for clearing)
                for header_name, header_value in extra_headers_on_success:
                    self.send_header(header_name, header_value)
                    print(f"DEBUG: Sent extra header: {header_name}: {header_value}")
                self.end_headers()
                response_body = json.dumps({"success": True, "message": message}).encode('utf-8')
                self.wfile.write(response_body)
            else:
                self._send_response(status_code, {"error": message})
            return # Handled

        # --- Handle /remove_user ---
        elif path == '/remove_user':
            username = data.get('username')

            if not username:
                self._send_response(400, {"error": "Missing username"})
                return

            # --- Prevent deleting admin user ---
            if username == 'admin':
                print("Attempt denied to remove 'admin' user.")
                self._send_response(403, {"error": "Cannot remove the admin user."}) # Forbidden
                return
            # --- End admin check ---

            success = False
            message = "Failed to remove user."
            status_code = 500
            save_needed = False

            with data_lock: # Or use a dedicated user_data_lock
                if username not in user_password_store:
                    message = f"User '{username}' not found."
                    status_code = 404 # Not Found
                else:
                    del user_password_store[username]
                    save_needed = True
                    print(f"User '{username}' removed from memory.")

                if save_needed:
                    if save_user_data_to_sql():
                        success = True
                        message = f"User '{username}' removed successfully."
                        status_code = 200 # OK
                    else:
                        # CRITICAL: Failed to save. User removed from memory but not file.
                        # Consider reloading user data from file or other recovery.
                        success = False
                        message = f"User '{username}' removed from memory, but FAILED to save to file."
                        status_code = 500

            if success:
                 self._send_response(status_code, {"success": True, "message": message})
            else:
                 self._send_response(status_code, {"error": message})
            return # Handled
        
        elif self.path == "/api/users":
            self.handle_add_user()
            return # Handled
        elif self.path == "/api/users/remove":
            self.handle_remove_user(data)
        elif self.path == "/api/users/set":
            self.handle_reset_password(data)
        elif self.path == "/api/users/reset":
            self.handle_reset_password(data)

        # --- Handle /api/increment & /api/decrement ---
        elif path == '/api/increment':
            # ... (existing increment code remains the same) ...
            return # Handled
        elif path == '/api/decrement':
            # ... (existing decrement code remains the same) ...
            return # Handled

        # --- Handle unknown authenticated POST paths ---
        else:
            print(f"Authenticated POST request to unknown path: {path}")
            self._send_response(404, {"error": "API endpoint not found"})

# --- End of ColorDaysHandler modifications ---


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
