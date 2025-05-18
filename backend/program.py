import os

if "pip: command not found" in os.popen('pip --version').read(): # Check if pip is installed
    print("pip not found, attempting to install...")
    os.system('python ./get-pip.py')
    os.system('pip install --upgrade pip')

# Initialize required names to None. They will be populated if imports succeed.
InstalledAppFlow = None
google_discovery_service = None # This will hold the 'discovery' module

try:
    from google_auth_oauthlib.flow import InstalledAppFlow as IAF
    from googleapiclient import discovery as discovery_module
    
    # Assign to our module-level variables
    InstalledAppFlow = IAF
    google_discovery_service = discovery_module
    print("Google OAuth libraries found and imported.")
except ImportError:
    print("One or more Google OAuth libraries not found, attempting to install...")
    install_cmd = 'pip install --upgrade google-auth-oauthlib google-api-python-client requests'
    print(f"Running: {install_cmd}")
    return_code = os.system(install_cmd)
    if return_code == 0:
        print("Installation attempt successful. Re-attempting import...")
        try:
            # Re-import and assign to the module-level variables using globals()
            # to ensure they are updated in the module's scope.
            from google_auth_oauthlib.flow import InstalledAppFlow as IAF_retry
            from googleapiclient import discovery as discovery_module_retry
            
            globals()['InstalledAppFlow'] = IAF_retry
            globals()['google_discovery_service'] = discovery_module_retry
            print("Libraries imported successfully after installation.")
        except ImportError:
            print("!!! CRITICAL: Failed to import libraries even after installation. OAuth will not work. Please restart the server.")
            # Ensure they remain None if the retry fails
            globals()['InstalledAppFlow'] = None
            globals()['google_discovery_service'] = None
    else:
        print(f"!!! CRITICAL: Installation failed with code {return_code}. Please install 'google-auth-oauthlib' and 'google-api-python-client' manually and restart the server.")
        globals()['InstalledAppFlow'] = None
        globals()['google_discovery_service'] = None

# Check if imports were successful
if InstalledAppFlow is None or google_discovery_service is None:
    print("!!! WARNING: Google OAuth libraries could not be loaded. Google login will be disabled.")
    # Ensure they are defined as None if not already, to prevent NameErrors later if checked.
    if 'InstalledAppFlow' not in globals() or globals()['InstalledAppFlow'] is None:
        InstalledAppFlow = None
    if 'google_discovery_service' not in globals() or globals()['google_discovery_service'] is None:
        google_discovery_service = None

import http.server
import socketserver
import json
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
import binascii # <-- For converting bytes to hex and back

# --- Configuration ---
BACKEND_DIR = Path(__file__).parent.resolve()
FRONTEND_DIR = (BACKEND_DIR.parent / 'frontend').resolve()
DATA_DIR = (BACKEND_DIR / 'data').resolve()
SQL_FILE_PATH = DATA_DIR / 'tables.sql' # Path to the SQL data file
CLASSES_SQL_FILE_PATH = DATA_DIR / 'classes.sql' # Path to the classes data file
LOGINS_SQL_FILE_PATH = DATA_DIR / 'logins.sql' # Path to the SQL logins file <--- NEW
HOST = 'localhost' # Or '0.0.0.0' to be accessible on your network
PORT = 8000 # Choose a port
SUPPORTED_CLASSES = [] # Must match menu.html and initial tables.sql

# --- Google OAuth Configuration ---
CLIENT_SECRETS_FILE = DATA_DIR / 'client_secret.json' # Path to your client_secret.json
GOOGLE_SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
GOOGLE_REDIRECT_URI = f'http://{HOST}:{PORT}/oauth2callback' # Must match one in client_secret.json and Google Console

# --- Secure Login Configuration (Using hashlib.pbkdf2_hmac) ---

# Parameters for PBKDF2
HASH_ALGORITHM = 'sha256'
# Iterations: Higher is more secure but slower. Start high (e.g., 260000+)
# Adjust based on your server performance and security needs.
# OWASP recommendation (as of late 2023) is 600,000 for PBKDF2-HMAC-SHA256
ITERATIONS = 390000 # Example value, tune as needed
SALT_BYTES = 16     # Size of the salt (16 bytes is common)
DK_LENGTH = 32      # Desired key length in bytes (e.g., 32 for SHA256)

# --- Role Configuration ---
ADMIN_ROLE = 'administrator'
TEACHER_ROLE = 'teacher'
DEFAULT_ROLE_FOR_NEW_USERS = TEACHER_ROLE # Default role for users created without a specified role
# --- End Role Configuration ---

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
    # Ensure stored_password_info is the expected dictionary structure
    if not isinstance(stored_password_info, dict) or 'password_hash' not in stored_password_info:
        print(f"Error: Invalid stored_password_info structure for user '{username}'. Expected a dict with 'password_hash'.")
        return False, []
    
    password_hash = stored_password_info['password_hash']
    extra_cookie_headers = [] # Initialize for cookies that might be set on successful pre-gen password login

    # 1. Handle special, non-loginable password states or unset passwords
    # These states mean the user cannot log in with a password.
    if not password_hash or \
       password_hash.upper() == '_NULL_' or \
       password_hash == 'NOT_SET' or \
       password_hash == '_GOOGLE_AUTH_USER_':
        
        if password_hash == '_GOOGLE_AUTH_USER_':
            print(f"Login attempt for Google OAuth user '{username}' with password. Denied.")
        elif not password_hash or password_hash.upper() == '_NULL_' or password_hash == 'NOT_SET':
            print(f"Login attempt for user '{username}' with unset, null, or 'NOT_SET' password state.")
        else: # Should not happen if above conditions are exhaustive for non-loginable
            print(f"Login attempt for user '{username}' with an unhandled special password state: {password_hash}")
        return False, []

    # 2. Handle pre-generated passwords (e.g., _password123_)
    # These are temporary passwords that usually require a change.
    # This check explicitly excludes _NULL_ and _GOOGLE_AUTH_USER_ due to the checks above.
    if password_hash.startswith('_') and password_hash.endswith('_'):
        # Extract the actual password part from within the underscores
        _stored_actual_password_ = password_hash[1:-1] 
        if _stored_actual_password_ == provided_password:
            print(f"User '{username}' logged in with pregenerated password. Setting change password cookie.")
            # Create a cookie to indicate that a password change is required/prompted
            change_pw_cookie_headers = create_cookies(
                CHANGE_PASSWORD_COOKIE_NAME,
                "not-required", # Value indicates verification (old pass) isn't needed for change
                path='/', 
                httponly=False # Allow JS to read this to manage UI for password change
            )
            return True, change_pw_cookie_headers
        else:
            # Pregenerated password was provided, but it didn't match
            print(f"Pregenerated password verification failed for user: {username}")
            return False, []

    # 3. Handle normally hashed passwords (format: salt_hex:key_hex)
    # This is the standard case for secure password storage.
    # We only proceed here if password_hash is not a special state and not a pre-generated one.
    # It must contain a ':' to be a valid salt:key pair.
    if ':' not in password_hash:
        # If it's not pre-generated and doesn't have a colon, it's an invalid format.
        print(f"Error: Unrecognized or invalid password_hash format ('{password_hash}') for user '{username}'. Expected 'salt:key'.")
        return False, []

    try:
        salt_hex, key_hex = password_hash.split(':')
        salt = binascii.unhexlify(salt_hex)
        stored_key = binascii.unhexlify(key_hex)
    except (ValueError, binascii.Error):
        # Invalid format or hex decoding failed
        print(f"Error: Invalid stored password format for hash starting with '{salt_hex[:8]}...' for user '{username}'")
        return False, []

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
    if not is_match:
        print(f"Password hash mismatch for user '{username}'.")
    # For standard hash verification, no extra cookies are typically set by this function itself.
    # The login handler will set session cookies if is_match is True.
    return is_match, []

# --- User Credentials Store (Loaded from logins.sql) --- <--- MODIFIED
# This dictionary will be populated by load_user_data_from_sql()
user_password_store = {}
# --- End User Credentials Store ---

# --- Session Configuration ---
USERNAME_COOKIE_NAME = "ColorDaysUser"
SESSION_COOKIE_NAME = "ColorDaysSession"
VALID_SESSION_VALUE = "user_is_logged_in_secret_value" # Replace with a secure, random session ID mechanism
CHANGE_PASSWORD_COOKIE_NAME = "ChangePasswordVerificationNotNeeded" # For the change password flow
GOOGLE_COOKIE_NAME = "GoogleAuthUser" # For Google OAuth users
SQL_COOKIE_NAME = "SQLAuthUser" # For SQL users
# --- End Session Configuration ---


# --- In-Memory Data Store and Lock ---
data_store = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
data_lock = threading.RLock()
class_data_store = [] # To store data from classes.sql as a list of dicts

def get_current_user_info(handler_instance): # Returns username_key, role
    """
    Retrieves the authenticated user's key (as used in user_password_store) and their role.
    """
    cookies = handler_instance.get_cookies()
    
    username_key_in_store = None
    # Prioritize specific auth cookies that hold the exact key from user_password_store
    sql_auth_cookie = cookies.get(SQL_COOKIE_NAME)
    if sql_auth_cookie and sql_auth_cookie.value in user_password_store:
        username_key_in_store = sql_auth_cookie.value
    
    if not username_key_in_store:
        google_auth_cookie = cookies.get(GOOGLE_COOKIE_NAME)
        if google_auth_cookie and google_auth_cookie.value in user_password_store:
            username_key_in_store = google_auth_cookie.value

    # Fallback for USERNAME_COOKIE_NAME if it directly matches a key (less common for Google users)
    if not username_key_in_store:
        username_cookie = cookies.get(USERNAME_COOKIE_NAME)
        if username_cookie and username_cookie.value in user_password_store:
            username_key_in_store = username_cookie.value

    if username_key_in_store:
        user_data = user_password_store.get(username_key_in_store)
        if user_data:
            return username_key_in_store, user_data.get('role', DEFAULT_ROLE_FOR_NEW_USERS) # Default if role somehow missing
    return None, None

def is_user_using_oauth(username, self):
    user_data = user_password_store.get(username) # username here is the key in user_password_store
    if user_data and user_data.get('password_hash') == '_GOOGLE_AUTH_USER_':
        print(f"User '{username}' is using Google OAuth. Password change not allowed.")
        return True
    return False

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

# --- Parsing for classes.sql ---
def parse_classes_sql_line(line):
    """Parses a single INSERT statement line for the classes table."""
    # Regex for: INSERT INTO classes (class, teacher, counts1, couts2, couts3) VALUES ('1.A', 'name', 'F', 'F', 'F');
    # Note the typo 'couts2' and 'couts3' in the SQL file.
    match = re.match(
        r"INSERT INTO classes\s*\(\s*class\s*,\s*teacher\s*,\s*counts1\s*,\s*couts2\s*,\s*couts3\s*\)\s*VALUES\s*\(\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([TF])'\s*,\s*'([TF])'\s*,\s*'([TF])'\s*\);",
        line.strip(),
        re.IGNORECASE
    )
    if match:
        class_name, teacher, counts1, couts2, couts3 = match.groups()
        return {"class": class_name, "teacher": teacher, "counts1": counts1, "couts2": couts2, "couts3": couts3}
    else:
        # Ignore comments and empty lines silently
        if line.strip() and not line.strip().startswith('--') and not line.strip().upper().startswith('CREATE TABLE'):
             print(f"Warning: Could not parse classes line format: {line.strip()}")
        return None

# --- Parsing for logins.sql --- <--- NEW
def parse_logins_sql_line(line):
    """
    Parses a single valid INSERT line for the users table.
    Handles formats with and without profile_picture_url and role.
    Returns (username, password_hash, profile_picture_url) or None.
    """
    line = line.strip()

    # Skip empty lines or comments
    if not line or line.startswith('--'):
        return None

    # Must start with an actual INSERT line
    if not line.upper().startswith("INSERT INTO USERS"):
        return None

    # Generic parser for INSERT INTO users (...) VALUES (...)
    match = re.match(r"INSERT INTO users\s*\((.*?)\)\s*VALUES\s*\((.*?)\);", line, re.IGNORECASE)

    if match:
        columns_str, values_str = match.groups()
        columns = [col.strip().lower() for col in columns_str.split(',')]
        
        # Naive value splitting assuming values are simple strings in single quotes and no escaped quotes/commas within values
        value_parts = []
        temp_val = ""
        in_string_literal = False
        for char_idx, char_val in enumerate(values_str):
            if char_val == "'":
                if in_string_literal and char_idx + 1 < len(values_str) and values_str[char_idx+1] == "'": # Escaped quote ''
                    temp_val += "'"
                    # Skip next char as it's part of escaped quote, but regex for this is hard
                    # This simple parser doesn't handle escaped quotes robustly.
                    # For this app, assume simple non-escaped values.
                else:
                    in_string_literal = not in_string_literal
                    if not in_string_literal: # End of a string literal
                        value_parts.append(temp_val)
                        temp_val = ""
            elif in_string_literal:
                temp_val += char_val
        
        if len(columns) != len(value_parts):
            print(f"Warning: Column count ({len(columns)}) doesn't match value count ({len(value_parts)}) in logins line: {line.strip()}")
            return None
    
        parsed_data = dict(zip(columns, value_parts))
        username = parsed_data.get('username')
        password_hash = parsed_data.get('password_hash')
        profile_picture_url = parsed_data.get('profile_picture_url', '_NULL_')
        role = parsed_data.get('role') # Get role

        if not role: # If role column is missing or value is empty/None from parsed_data
            # This handles cases where the 'role' column might not be in the INSERT statement
            print(f"Warning: 'role' not found or empty for user '{username}' in logins line: {line.strip()}. Assigning default role: '{DEFAULT_ROLE_FOR_NEW_USERS}'.")
            role = DEFAULT_ROLE_FOR_NEW_USERS

        if not username or not password_hash:
            print(f"Warning: Missing username or password_hash in parsed data from logins line: {line.strip()}")
            return None
        # Basic validation for password_hash format (can be expanded)
        if not (':' in password_hash or password_hash.upper() == '_NULL_' or password_hash.upper() == 'GOOGLE_AUTH_USER' or (password_hash.startswith('_') and password_hash.endswith('_'))):
            print(f"Warning: User '{username}' has unrecognized password_hash format: '{password_hash}' in line: {line.strip()}. Will be loaded but may cause issues.")
            return None
        return username, password_hash, profile_picture_url, role
    else:
        # Only print warning for lines that look like they should be INSERTs but don't match
        if line.upper().startswith("INSERT INTO USERS"):
            print(f"Warning: Could not parse logins line format (regex mismatch): {line.strip()}")
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

# --- Loading for classes.sql ---
def load_class_data_from_sql():
    """Loads data from classes.sql into the in-memory class_data_store."""
    global class_data_store
    print(f"Attempting to load class data from: {CLASSES_SQL_FILE_PATH}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp_class_store = []
    file_exists = CLASSES_SQL_FILE_PATH.exists()
    classes_loaded_count = 0

    if file_exists:
        try:
            with open(CLASSES_SQL_FILE_PATH, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    parsed = parse_classes_sql_line(line)
                    if parsed:
                        temp_class_store.append(parsed)
                        classes_loaded_count += 1
            print(f"Loaded {classes_loaded_count} class(es) from {CLASSES_SQL_FILE_PATH}.")
        except Exception as e:
            print(f"!!! ERROR reading or parsing {CLASSES_SQL_FILE_PATH}: {e}. Class data store might be empty or incomplete.")
            temp_class_store.clear()
    else:
        print(f"Warning: {CLASSES_SQL_FILE_PATH} not found. No classes loaded. Class management will start with an empty list.")

    # Update the global data store under lock
    with data_lock: # Reusing data_lock for simplicity
        class_data_store = temp_class_store

    print("Class data loading complete.")

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
                        username, password_hash, profile_picture_url, role = parsed # Unpack role
                        temp_user_store[username] = {
                            'password_hash': password_hash,
                            'profile_picture_url': profile_picture_url if profile_picture_url else '_NULL_',
                            'role': role # Store role
                        }
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
        
# --- Saving for classes.sql ---
def save_class_data_to_sql():
    """Saves the current in-memory class_data_store back to classes.sql. Returns True on success, False on failure."""
    global class_data_store
    print(f"Attempting to save class data to: {CLASSES_SQL_FILE_PATH}")
    with data_lock: # Reusing data_lock
        try:
            sql_lines = []
            sql_lines.append(f"-- Class data saved on {datetime.datetime.now().isoformat()} --")
            sql_lines.append("")

            # Sort by class name for consistent file output, if desired, or keep original order
            # sorted_class_data = sorted(class_data_store, key=lambda x: x['class'])
            # For now, saving in current order (append order for new items)
            for class_item in class_data_store:
                # Basic escaping for class name and teacher (should be sufficient if they don't contain quotes)
                safe_class_name = class_item['class'].replace("'", "''")
                safe_teacher = class_item['teacher'].replace("'", "''")
                insert_statement = (
                    f"INSERT INTO classes (class, teacher, counts1, couts2, couts3) VALUES "
                    f"('{safe_class_name}', '{safe_teacher}', '{class_item['counts1']}', '{class_item['couts2']}', '{class_item['couts3']}');"
                )
                sql_lines.append(insert_statement)

            with open(CLASSES_SQL_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write("\n".join(sql_lines))
                f.write("\n")
            print(f"Class data successfully saved to {CLASSES_SQL_FILE_PATH}")
            return True
        except Exception as e:
            print(f"!!! UNEXPECTED ERROR during save_class_data_to_sql:")
            print(traceback.format_exc())
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
            for username, user_data in sorted(user_password_store.items()):
                # Basic escaping for username (should be sufficient if usernames don't contain quotes)
                safe_username = username.replace("'", "''")
                password_hash = user_data['password_hash'] # Already hex or special string
                profile_pic_url = user_data.get('profile_picture_url', '_NULL_')
                role = user_data.get('role', DEFAULT_ROLE_FOR_NEW_USERS) # Get role, default if missing
                safe_profile_pic_url = profile_pic_url.replace("'", "''") if profile_pic_url else '_NULL_'
                safe_role = role.replace("'", "''") # Escape role
                insert_statement = f"INSERT INTO users (username, password_hash, role, profile_picture_url) VALUES ('{safe_username}', '{password_hash}', '{safe_role}', '{safe_profile_pic_url}');"
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

# --- Function to save main config.json ---
def save_main_config_to_json(new_oauth_data):
    """
    Reads the existing config.json, updates OAuth specific keys,
    and writes the entire config back.
    Returns True on success, False on failure.
    """
    config_file_path = DATA_DIR / 'config.json'
    print(f"Attempting to update OAuth settings in: {config_file_path}")

    with data_lock: # Reuse data_lock for simplicity
        try:
            current_config = {}
            if config_file_path.exists():
                with open(config_file_path, 'r', encoding='utf-8') as f:
                    current_config = json.load(f)
            
            # Update only the OAuth related keys from the new_oauth_data
            current_config['oauth_eneabled'] = new_oauth_data.get('oauth_eneabled', current_config.get('oauth_eneabled', 'false'))
            current_config['allowed_oauth_domains'] = new_oauth_data.get('allowed_oauth_domains', current_config.get('allowed_oauth_domains', []))

            with open(config_file_path, 'w', encoding='utf-8') as f:
                json.dump(current_config, f, indent=4) # Pretty print with indent
            
            print(f"OAuth settings successfully updated in {config_file_path}")
            return True
        except Exception as e:
            print(f"!!! UNEXPECTED ERROR during save_main_config_to_json:")
            print(traceback.format_exc())
            return False

# --- End function to save main config.json ---

# --- Module-level Handler Functions for Increment/Decrement ---

def handle_increment_module(handler_instance, data, request_path):
    class_name = data.get('className')
    type_val = data.get('type')
    points_val = data.get('points')

    # Basic validation
    if not all([class_name, type_val, points_val is not None]):
        handler_instance._send_response(400, {"error": "Missing data: className, type, or points"})
        return
    if type_val not in ['student', 'teacher']:
        handler_instance._send_response(400, {"error": "Invalid type"})
        return
    if not isinstance(points_val, int) or not (0 <= points_val <= 6):
        handler_instance._send_response(400, {"error": "Invalid points value"})
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
            print(f"!!! UNEXPECTED ERROR during POST {request_path} operation (within lock):") # Use request_path
            print(traceback.format_exc())
            success = False
            message = "An internal error occurred during the increment operation."
            status_code = 500

    if status_code == 200:
        handler_instance._send_response(status_code, {"success": success, "message": message})
    else:
        handler_instance._send_response(status_code, {"error": message})
    return # Handled

def handle_decrement_module(handler_instance, data, request_path):
    class_name = data.get('className')
    type_val = data.get('type')
    points_val = data.get('points')

    # Basic validation
    if not all([class_name, type_val, points_val is not None]):
        handler_instance._send_response(400, {"error": "Missing data: className, type, or points"})
        return
    if type_val not in ['student', 'teacher']:
        handler_instance._send_response(400, {"error": "Invalid type"})
        return
    if not isinstance(points_val, int) or not (0 <= points_val <= 6):
        handler_instance._send_response(400, {"error": "Invalid points value"})
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
                success = False
                message = "Count already zero"
                status_code = 400
                save_needed = False

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
            print(f"!!! UNEXPECTED ERROR during POST {request_path} operation (within lock):") # Use request_path
            print(traceback.format_exc())
            success = False
            message = "An internal error occurred during the decrement operation."
            status_code = 500

    if status_code == 200:
        handler_instance._send_response(status_code, {"success": success, "message": message})
    else:
        handler_instance._send_response(status_code, {"error": message})
    return # Handled

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
                if content_type == 'application/json':
                    if isinstance(data, bytes): # Data is already bytes (e.g., pre-read JSON file)
                        response_body = data
                    else: # Data is a Python object (dict/list) to be serialized
                        response_body = json.dumps(data).encode('utf-8')
                else: # Not JSON content type, assume data is already in correct byte format or is a Python object for non-JSON
                    response_body = data
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
        # RBAC Check
        _user_key, user_role = get_current_user_info(self)
        if not self.is_logged_in() or user_role != ADMIN_ROLE:
            self._send_response(403, {"error": "Forbidden: Administrator access required."})
            return

        # Use in-memory user_password_store, no need to reload from file here
        user_list = []
        with data_lock: # Access user_password_store safely
            for username_key, user_data_val in user_password_store.items():
                password_hash = user_data_val['password_hash']
                role = user_data_val.get('role', DEFAULT_ROLE_FOR_NEW_USERS) # Get role

                # Determine password status for frontend
                status = "set" # Default
                if password_hash is None or password_hash.upper() == '_NULL_':
                    status = "not_set"
                elif password_hash == '_GOOGLE_AUTH_USER_':
                    status = "google_auth_user"
                # Check for pre-generated passwords like _password_, but not _NULL_ or _GOOGLE_AUTH_USER_
                elif password_hash.startswith('_') and password_hash.endswith('_') and \
                     password_hash.upper() != '_NULL_' and password_hash.upper() != '_GOOGLE_AUTH_USER_':
                    status = password_hash[1:-1] # Extract the pre-generated password
                
                user_list.append({
                    "username": username_key,
                    "password": status, # 'password' field name is for frontend compatibility
                    "role": role
                })
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
            user_password_store[username] = {
                'password_hash': 'NOT_SET', # Or use "_NOT_SET_" if you prefer the underscore convention
                'profile_picture_url': '_NULL_',
                'role': DEFAULT_ROLE_FOR_NEW_USERS # Assign default role
            }

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
                    
        # RBAC check (already done by caller in do_POST, but good for standalone use)
        _user_key, current_user_role = get_current_user_info(self)
        if not self.is_logged_in() or current_user_role != ADMIN_ROLE:
            self._send_response(403, {"error": "Forbidden: Administrator access required."})
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
                # Check if it's a case issue by iterating keys
                found_user_case_insensitive = next((k for k in user_password_store if k.lower() == username.lower()), None)
                if found_user_case_insensitive:
                    message = f"User '{username}' not found (case mismatch? Found: '{found_user_case_insensitive}')."
                else:
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

        # RBAC check (already done by caller in do_POST, but good for standalone use)
        # _user_key, current_user_role = get_current_user_info(self)
        # if not self.is_logged_in() or current_user_role != ADMIN_ROLE:
        #     self._send_response(403, {"error": "Forbidden: Administrator access required."})
        #     return
        if is_user_using_oauth(username, self): # username is the key from user_password_store
            self._send_response(403, {"error": "Password change not allowed for Google OAuth users."})
            return

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
                    user_password_store[username]['password_hash'] = hashed # Only update hash
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

        # DEBUG: Print the requested path at the beginning of do_GET
        print(f"--- DEBUG: do_GET received request for path: '{path}', full self.path: '{self.path}' ---")

        user_key, user_role = get_current_user_info(self) # Get user info once

        if path == '/list_users':
            # --- Authentication Check ---
            if not self.is_logged_in():
                print(f"Denied GET request to {path} - User not logged in.")
                self._send_response(401, {"error": "Authentication required"})
                return
            # --- RBAC Check ---
            if user_role != ADMIN_ROLE:
                self._send_response(403, {"error": "Forbidden: Administrator access required."})
                return
            # --- End RBAC Check ---

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
        allowed_get_paths_during_change = ['/login.html', '/change-password.html', '/logout', '/change-password.js']
        # Add essential CSS/JS if needed for change-password.html
        allowed_get_paths_during_change.append('/style.css') # Also allow style.css if used by change-password.html

        # Block API GET requests if change is required (adjust allowed paths if needed)
        if is_logged_in_flag and password_change_required and path.startswith('/api/') and path not in allowed_get_paths_during_change:
            print(f"Denied GET request to API {path} - Password change required.")
            # For API endpoints, sending an error is usually better than redirecting
            self._send_response(403, {"error": "Password change required before accessing this API resource."})
            return
        # --- End Password Change Check for API GET ---

        elif path == '/api/users':
            # RBAC is handled inside handle_get_users
            if not self.is_logged_in(): # Basic auth check
                print(f"Denied GET request to {path} - User not logged in.")
                self._send_response(401, {"error": "Authentication required"})
                return
            
            print(f"Handling GET request for {path}") # Add log
            self.handle_get_users() # Call the handler function
            return # Make sure to return after handling

        elif path == '/api/classes':
            if not self.is_logged_in():
                print(f"Denied GET request to {path} - User not logged in.")
                self._send_response(401, {"error": "Authentication required"})
                return
        
            # RBAC Check
            # _user_key, current_user_role = get_current_user_info(self) # user_role is already available from the top of do_GET
            if user_role not in [ADMIN_ROLE, TEACHER_ROLE]: # Allow both Admin and Teacher
                self._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
                return
            
            with data_lock: # Ensure thread-safe read
                # Send a copy to avoid issues if it's modified elsewhere during serialization
                response_data = list(class_data_store) 
            self._send_response(200, response_data)
            return

        # API Endpoint: /api/counts?class=ClassName
        elif path == '/api/counts':
            if not self.is_logged_in():
                print(f"Denied GET request to {path} - User not logged in.")
                self._send_response(401, {"error": "Authentication required"})
                return

            # RBAC Check: Allow teachers and admins
            if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
                self._send_response(403, {"error": "Forbidden: Access denied for your role."})
                return

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

        # --- Google OAuth Endpoints (Moved to do_GET) ---
        elif path == '/login/google':
            print(f"--- DEBUG: Matched '/login/google' endpoint ---")
            try:
                if InstalledAppFlow is None:
                    print("!!! ERROR: InstalledAppFlow not available for Google OAuth.")
                    self._send_response(500, {"error": "Google OAuth component (InstalledAppFlow) missing on server."})
                    return

                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRETS_FILE, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI
                )
                auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline') # Added access_type for refresh token

                print(f"--- DEBUG: Redirecting to Google OAuth URL: {auth_url} ---")
                self.send_response(302)
                self.send_header('Location', auth_url)
                self.end_headers()
            except FileNotFoundError:
                print(f"!!! ERROR: {CLIENT_SECRETS_FILE} not found. Google OAuth will not work.")
                self._send_response(500, {"error": "Google OAuth configuration error (server-side)."})
            except Exception as e:
                print(f"!!! Error during Google OAuth initiation: {e}")
                print(traceback.format_exc())
                self._send_response(500, {"error": "Could not initiate Google login."})
            return

        elif path == '/oauth2callback':
            print(f"--- DEBUG: Matched '/oauth2callback' endpoint ---")
            try:
                code = query.get('code', [None])[0] # 'query' is available from start of do_GET
                if not code:
                    self._send_response(400, {"error": "Missing authorization code from Google."})
                    return

                if InstalledAppFlow is None or google_discovery_service is None:
                    print("!!! ERROR: OAuth components (InstalledAppFlow or discovery service) not available.")
                    self._send_response(500, {"error": "Google OAuth components missing on server."})
                    return

                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRETS_FILE, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI
                )
                flow.fetch_token(code=code)
                credentials = flow.credentials

                # Use the imported google_discovery_service module
                userinfo_service = google_discovery_service.build('oauth2', 'v2', credentials=credentials)
                user_info = userinfo_service.userinfo().get().execute()
                
                # DEBUG: Print user_info from Google
                print(f"--- DEBUG: User info from Google: {user_info} ---")

                _user_email_from_google = user_info.get('email') # Get the email as Google provides it
                # Ensure the email used for cookies and storage is stripped of any surrounding quotes.
                user_email = _user_email_from_google.strip('"') if _user_email_from_google else None

                user_name_from_google_raw = user_info.get('name', _user_email_from_google) # Get the raw name, fallback to original email from Google
                profile_picture = user_info.get('picture') # Get profile picture URL

                # Determine the name to be used for the cookie
                name_for_cookie = ''
                if user_email: # If we have an email from Google (now stripped)
                    name_for_cookie = user_email.split('@', 1)[0] # Take the part before the first '@'
                elif user_name_from_google_raw: # Fallback to Google display name if email is somehow missing
                    name_for_cookie = user_name_from_google_raw.strip('"') # Ensure raw name is also stripped if used
                # If both email and raw name are missing, name_for_cookie will be empty.
                # This is unlikely with Google OAuth scopes requesting email.

                print(f"--- DEBUG: OAuth - Email: '{user_email}', Raw Google Name: '{user_name_from_google_raw}', Picture: '{profile_picture}', Generated Name for Cookie: '{name_for_cookie}' ---")

                if not user_email:
                    self._send_response(400, {"error": "Could not retrieve email from Google."})
                    return

                with data_lock:
                    if user_email not in user_password_store:
                        print(f"--- DEBUG: New Google user '{user_email}' (name: '{name_for_cookie}'). Adding to store. ---")
                        user_password_store[user_email] = {
                            'password_hash': '_GOOGLE_AUTH_USER_',
                            'profile_picture_url': profile_picture if profile_picture else '_NULL_',
                            'role': DEFAULT_ROLE_FOR_NEW_USERS # Assign default role for new Google users
                        }
                        save_user_data_to_sql()

                all_cookies = create_cookies(USERNAME_COOKIE_NAME, name_for_cookie, path='/', httponly=False) + \
                              create_cookies(SESSION_COOKIE_NAME, VALID_SESSION_VALUE, path='/') + \
                              create_cookie_clear_headers(CHANGE_PASSWORD_COOKIE_NAME, path='/') + \
                              create_cookies(GOOGLE_COOKIE_NAME, user_email, path='/', httponly=False)
                
                # --- Send response headers MANUALLY for OAuth callback ---
                self.send_response(302) # Redirect
                self.send_header('Location', '/menu.html') # Redirect location
                # CORS Headers (important if the redirect target needs them, though usually not for 302)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
                self.send_header('Access-Control-Allow-Credentials', 'true')

                # Send EACH Set-Cookie header individually
                print(f"--- DEBUG: OAuth - Preparing to send {len(all_cookies)} cookie(s)... ---")
                for header_name, header_value in all_cookies:
                    self.send_header(header_name, header_value)
                    print(f"--- DEBUG: OAuth - Sent {header_name} header: {header_value} ---")
                
                self.end_headers()
                # No body needed for a 302 redirect
                print(f"--- DEBUG: OAuth successful for user '{name_for_cookie}', redirecting to /menu.html with cookies. ---")
                # self._send_response(302, headers={'Location': '/menu.html', **dict(all_cookies)}) # Old problematic line
            except Exception as e:
                print(f"!!! Error during Google OAuth callback: {e}")
                print(traceback.format_exc())
                self._send_response(500, {"error": "Google OAuth callback failed."})
            return

        elif path == '/api/data/config': # Serve the main config.json
            print(f"--- DEBUG: Matched request for '/backend/data/config.json' ---")
            config_file_path = DATA_DIR / 'config.json'
            if config_file_path.is_file():
                try:
                    with open(config_file_path, 'rb') as f:
                        content = f.read()
                    # _send_response handles CORS and content type if data is bytes
                    self._send_response(200, data=content, content_type='application/json')
                except Exception as e:
                    print(f"!!! Error serving {config_file_path}: {e}")
                    self._send_response(500, {"error": f"Error serving server configuration file: {e}"}, content_type='application/json')
            else:
                print(f"!!! CRITICAL: Server configuration file {config_file_path} not found.")
                self._send_response(404, {"error": "Server configuration file not found."}, content_type='application/json')
            return

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
            # --- Add Login Check for Change Password Page ---
            elif path == '/change-password.html' and not is_logged_in_flag:
                print(f"Denied GET request for {path} - User not logged in. Redirecting to login.")
                self.send_response(302) # Found (redirect)
                self.send_header('Location', '/login.html')
                self.end_headers()
                return # Stop processing
            # --- End Login Check ---
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
                # If it's not a recognized API endpoint or an existing file, return 404
                print(f"--- DEBUG: Path '{path}' did not match specific API or OAuth endpoints, and file not found at '{file_path}', sending 404. ---")
                self._send_response(404, {"error": "Resource not found", "requested_path": path}, content_type='application/json')

        except FileNotFoundError as e:
            print(f"File serving error (404): {e}")
            # Ensure the error message includes the path for better debugging
            # The 'path' variable here is the one parsed at the start of do_GET
            print(f"--- DEBUG: FileNotFoundError for path '{path}', sending 404. ---")
            self._send_response(404, {"error": "File not found", "requested_path": path}, content_type='application/json')

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

        content_length = int(self.headers.get('Content-Length', 0))
        post_body_bytes = b'' # Use a more descriptive name for the raw bytes
        if content_length > 0:
            post_body_bytes = self.rfile.read(content_length)
        # Note: We don't immediately reject empty bodies here,
        # as /logout allows it. Specific endpoints will check if they need a body.

        # --- LOGIN Endpoint ---
        if path == '/login':
            # Login endpoint specifically requires a non-empty body
            if not post_body_bytes:
                self._send_response(400, {"error": "Missing request body for login"})
                return
            try:
                credentials = json.loads(post_body_bytes) # Use the correctly read body
                username = credentials.get('username')
                submitted_password = credentials.get('password')
                print(f"DEBUG: Login attempt for username: '{username}'") # Log username


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
                    # Ensure username doesn't have accidental surrounding quotes before setting cookie
                    cleaned_username = username.strip('"') if username else ""
                    
                    # Use cleaned_username for the cookie
                    user_cookie_headers = create_cookies(USERNAME_COOKIE_NAME, cleaned_username, path='/', httponly=False)
                    session_cookie_headers = create_cookies(SESSION_COOKIE_NAME, VALID_SESSION_VALUE, path='/')
                    sql_user_cookie_headers = create_cookies(SQL_COOKIE_NAME, username, path='/', httponly=False) # Set the SQL auth cookie

                    # --- COMBINE standard cookies with any extra ones returned ---
                    all_cookie_headers = user_cookie_headers + session_cookie_headers + extra_cookie_headers + sql_user_cookie_headers
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

                    # Include role in login response
                    user_key_for_role = username # This is the key used to lookup in user_password_store
                    role = user_password_store.get(user_key_for_role, {}).get('role', DEFAULT_ROLE_FOR_NEW_USERS)

                    response_payload = {
                        "success": True,
                        "message": "Login successful",
                        "username": cleaned_username, # The display username for the cookie
                        "role": role
                    }
                    response_body = json.dumps(response_payload).encode('utf-8')
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
            sql_user_clear_headers = create_cookie_clear_headers(SQL_COOKIE_NAME, path='/') # Clear SQL user cookie if used
            google_auth_clear_headers = create_cookie_clear_headers(GOOGLE_COOKIE_NAME, path='/') # Clear Google auth cookie if used
            all_clear_headers = session_clear_headers + user_clear_headers + change_pw_clear_headers + sql_user_clear_headers + google_auth_clear_headers
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

        # --- For all other POST endpoints below, a JSON body is generally expected ---
        # (and authentication is required)

        # --- Password Change Check for POST ---
        # Must happen *after* login check but *before* executing protected endpoint logic
        cookies = self.get_cookies() # Get fresh cookies for POST check
        password_change_required = cookies.get(CHANGE_PASSWORD_COOKIE_NAME)

        # Define POST paths allowed even if a password change is "pending" (e.g., from pre-gen password)
        # /api/auth/change is the endpoint TO change the password.
        allowed_post_paths_during_change = ['/login', '/logout', '/api/auth/change']

        # If the "ChangePasswordVerificationNotNeeded" cookie exists, it means they logged in with a pre-gen password.
        # They should only be able to call /api/auth/change or /logout.
        if password_change_required and password_change_required.value == "not-required" and path not in allowed_post_paths_during_change:
            print(f"Denied POST request to {path} - Password change required.")
            self._send_response(403, {"error": "Password change required before performing this action."})
            return
        # --- End Password Change Check ---

        # --- RBAC: Get current user's role for protected endpoints ---
        user_key_for_rbac, current_user_role = get_current_user_info(self)
        if not self.is_logged_in(): # Should be caught by password_change_required logic too, but good to double check
            self._send_response(401, {"error": "Authentication required for this action."})
            return


        # --- Protected Endpoints below require login ---
        print(f"Processing authenticated POST request to {path}...") # Log access

        # Parse JSON body (already read, just need to decode)
        try:
            # Most subsequent endpoints expect a JSON body.
            # If post_body_bytes is empty here, it means content_length was 0 and it wasn't /login or /logout.
            if not post_body_bytes:
                self._send_response(400, {"error": "Missing JSON payload for this endpoint"})
                return
            data = json.loads(post_body_bytes)
        except json.JSONDecodeError:
            self._send_response(400, {"error": "Invalid JSON payload"})
            return
        # --- Handle /add_user ---
        if path == '/add_user':
            # RBAC Check
            if current_user_role != ADMIN_ROLE:
                self._send_response(403, {"error": "Forbidden: Administrator access required."})
                return

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
                            user_password_store[username] = {
                                'password_hash': hashed_pw,
                                'profile_picture_url': '_NULL_',
                                'role': DEFAULT_ROLE_FOR_NEW_USERS # Assign default role
                            }
                            save_needed = True
                            print(f"User '{username}' added to memory.")
                        except Exception as e:
                            print(f"!!! Error hashing password for {username}: {e}")
                            message = "Server error during password hashing."
                            status_code = 500
                    elif pass_null == True and username in user_password_store: # User exists, setting password to NULL
                        user_password_store[username]['password_hash'] = "_NULL_"
                        save_needed = True # This branch is unlikely to be hit due to outer check, but if it were, it's fine.
                    else:
                        hashed_pw = "_NULL_" # Explicitly set to null
                        user_password_store[username] = { # Ensure a dictionary is stored
                            'password_hash': hashed_pw,
                            'profile_picture_url': '_NULL_', # Default profile picture URL
                            'role': DEFAULT_ROLE_FOR_NEW_USERS # Assign default role
                        }
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

        # --- Handle /api/classes/add ---
        elif path == '/api/classes/add':
            # RBAC Check
            if current_user_role != ADMIN_ROLE:
                self._send_response(403, {"error": "Forbidden: Administrator access required."})
                return

            class_name = data.get('class')
            teacher = data.get('teacher')
            counts1 = data.get('counts1', 'F') # Default to 'F' if not provided
            counts2 = data.get('couts2', 'F')  # Use 'couts2' to match SQL and JS
            counts3 = data.get('couts3', 'F')  # Use 'couts3' to match SQL and JS

            if not class_name or not teacher:
                self._send_response(400, {"error": "Missing class name or teacher"})
                return
            if counts1 not in ['T', 'F'] or counts2 not in ['T', 'F'] or counts3 not in ['T', 'F']:
                self._send_response(400, {"error": "Invalid counts values (must be T or F)"})
                return

            success = False
            message = "Failed to add class."
            status_code = 500

            with data_lock:
                if any(c['class'] == class_name for c in class_data_store):
                    message = f"Class '{class_name}' already exists."
                    status_code = 409 # Conflict
                else:
                    new_class = {
                        "class": class_name, "teacher": teacher,
                        "counts1": counts1, "couts2": counts2, "couts3": counts3
                    }
                    class_data_store.append(new_class)
                    # Sort the class_data_store alphabetically by class name
                    class_data_store.sort(key=lambda x: x['class'])
                    if save_class_data_to_sql():
                        success = True
                        message = f"Class '{class_name}' added successfully."
                        status_code = 201 # Created
                    else:
                        # Revert add if save fails
                        class_data_store.pop() 
                        message = f"Failed to save class '{class_name}' to file."
                        status_code = 500
            
            if success:
                self._send_response(status_code, {"success": True, "message": message})
            else:
                self._send_response(status_code, {"error": message})
            return

        # --- Handle /api/classes/remove ---
        elif path == '/api/classes/remove':
            # RBAC Check
            if current_user_role != ADMIN_ROLE:
                self._send_response(403, {"error": "Forbidden: Administrator access required."})
                return

            class_name_to_remove = data.get('class')
            if not class_name_to_remove:
                self._send_response(400, {"error": "Missing class name to remove"})
                return

            success = False
            message = "Failed to remove class."
            status_code = 500

            with data_lock:
                original_len = len(class_data_store)
                class_data_store[:] = [c for c in class_data_store if c['class'] != class_name_to_remove]
                if len(class_data_store) < original_len: # If something was removed
                    if save_class_data_to_sql():
                        success = True
                        message = f"Class '{class_name_to_remove}' removed successfully."
                        status_code = 200
                    else:
                        # This is tricky, if save fails, we should ideally reload or revert.
                        # For now, log error, data in memory is changed but not file.
                        message = f"Class '{class_name_to_remove}' removed from memory, but FAILED to save to file."
                        status_code = 500 # Internal Server Error
                else:
                    message = f"Class '{class_name_to_remove}' not found."
                    status_code = 404 # Not Found

            if success:
                self._send_response(status_code, {"success": True, "message": message})
            else:
                self._send_response(status_code, {"error": message})
            return

        # --- Handle /api/classes/update_counts ---
        elif path == '/api/classes/update_counts':
            # RBAC Check
            if current_user_role != ADMIN_ROLE:
                self._send_response(403, {"error": "Forbidden: Administrator access required."})
                return

            class_name = data.get('class')
            count_field = data.get('countField') # e.g., "counts1", "couts2", "couts3"
            new_value = data.get('value')       # 'T' or 'F'

            if not all([class_name, count_field, new_value is not None]): # new_value can be 'F'
                self._send_response(400, {"error": "Missing class, countField, or value"})
                return
            
            # Ensure count_field matches the keys used in your data (including the typo)
            valid_count_fields = ["counts1", "couts2", "couts3"]
            if count_field not in valid_count_fields:
                self._send_response(400, {"error": f"Invalid countField. Must be one of {valid_count_fields}"})
                return
            
            if new_value not in ['T', 'F']:
                self._send_response(400, {"error": "Invalid value. Must be 'T' or 'F'"})
                return

            success = False
            message = "Failed to update class count."
            status_code = 500

            with data_lock:
                class_to_update = next((cls_item for cls_item in class_data_store if cls_item['class'] == class_name), None)
                
                if not class_to_update:
                    message = f"Class '{class_name}' not found."
                    status_code = 404
                else:
                    class_to_update[count_field] = new_value
                    if save_class_data_to_sql():
                        success = True
                        message = f"Count '{count_field}' for class '{class_name}' updated to '{new_value}'."
                        status_code = 200
                    else:
                        message = f"Count for class '{class_name}' updated in memory, but FAILED to save to file. Consider restarting server or checking file permissions."
                        status_code = 500 # Keep as 500, as the persistent save failed
            
            if success:
                self._send_response(status_code, {"success": True, "message": message})
            else:
                self._send_response(status_code, {"error": message})
            return

        # --- Handle /change_password ---
        elif path == '/api/auth/change':
            # user_key_for_rbac (user's actual key in user_password_store) is already available
            if not user_key_for_rbac: # Should be caught by is_logged_in earlier
                print("Error: Username cookie missing in authenticated /api/auth/change request.")
                self._send_response(401, {"error": "Authentication error: User identity not found."})
                return
            if is_user_using_oauth(user_key_for_rbac, self): # Pass the correct key
                self._send_response(403, {"error": "Password change not allowed for Google OAuth users."})
                return
            username_for_messages = user_key_for_rbac # For logging/messages

            old_password = data.get('oldPassword')
            new_password = data.get('newPassword') # Get new password from request

            # --- Check for the cookie and force verification if present ---
            cookies = self.get_cookies()
            if cookies.get(CHANGE_PASSWORD_COOKIE_NAME):
                print(f"DEBUG: Cookie '{CHANGE_PASSWORD_COOKIE_NAME}' found. Forcing verification_needed to False.")
                verification_needed = False # Override whatever the client sent
            # --- End cookie check ---
            
            if not user_key_for_rbac or not new_password: # Check against the actual key
                self._send_response(400, {"error": "Missing username or new password"})
                return

            success = False
            message = "Failed to change password."
            status_code = 500
            save_needed = False

            with data_lock: # Or use a dedicated user_data_lock
                stored_user_data = user_password_store.get(user_key_for_rbac)

                if not stored_user_data:
                    message = f"User '{username_for_messages}' not found."
                    status_code = 404 # Not Found
                else:
                    if verification_needed == True:
                        # verify_password returns a tuple (bool, headers)
                        is_old_valid, _ = verify_password(stored_user_data, old_password, username_for_messages)
                        if not is_old_valid:
                            message = "Old password verification failed."
                            status_code = 401
                            self._send_response(status_code, {"error": message})
                            return

                    try:
                        hashed_pw = hash_password(new_password)
                        user_password_store[user_key_for_rbac]['password_hash'] = hashed_pw # Update only hash
                        save_needed = True
                        print(f"Password changed in memory for user '{username_for_messages}'.")
                    except Exception as e:
                        print(f"!!! Error hashing new password for {username_for_messages}: {e}")
                        message = "Server error during password hashing."
                        status_code = 500

                if save_needed:
                    if save_user_data_to_sql():
                        success = True
                        message = f"Password for user '{username_for_messages}' changed successfully."
                        status_code = 200 # OK
                    else:
                        success = False
                        message = f"Password changed in memory for '{username_for_messages}', but FAILED to save to file."
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
            # RBAC Check
            if current_user_role != ADMIN_ROLE:
                self._send_response(403, {"error": "Forbidden: Administrator access required."})
                return

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
        
        elif path == "/api/users": # POST to /api/users
            # RBAC check is inside handle_post_users, called after auth check
            self.handle_post_users() # This adds a user with 'NOT_SET' password
            return # Handled
        elif path == "/api/users/remove":
            # RBAC Check
            if current_user_role != ADMIN_ROLE:
                self._send_response(403, {"error": "Forbidden: Administrator access required."})
                return
            self.handle_remove_user(data)
            return # Handled
        elif path == "/api/users/set":
            # RBAC Check
            if current_user_role != ADMIN_ROLE:
                self._send_response(403, {"error": "Forbidden: Administrator access required."})
                return
            self.handle_reset_password(data)
            return # Handled
        elif path == "/api/users/reset": # Alias for /set
            # RBAC Check
            if current_user_role != ADMIN_ROLE:
                self._send_response(403, {"error": "Forbidden: Administrator access required."})
                return
            self.handle_reset_password(data)
            return # Handled

        # --- Handle /api/increment & /api/decrement ---
        elif path == '/api/increment':
            handle_increment_module(self, data, self.path)

        # --- Handle /api/decrement ---
        elif path == '/api/decrement':
            handle_decrement_module(self, data, self.path)

        # --- Handle /api/data/save/config ---
        elif path == '/api/data/save/config':
            # RBAC Check
            if current_user_role != ADMIN_ROLE:
                self._send_response(403, {"error": "Forbidden: Administrator access required."})
                return
            
            # Data is already parsed from the start of do_POST
            oauth_eneabled = data.get('oauth_eneabled')
            allowed_domains = data.get('allowed_oauth_domains')

            if oauth_eneabled is None or not isinstance(allowed_domains, list):
                self._send_response(400, {"error": "Invalid payload. 'oauth_eneabled' (string) and 'allowed_oauth_domains' (list) are required."})
                return
            
            # Ensure oauth_eneabled is "true" or "false"
            if oauth_eneabled not in ["true", "false"]:
                self._send_response(400, {"error": "'oauth_eneabled' must be the string 'true' or 'false'."})
                return

            if save_main_config_to_json(data):
                self._send_response(200, {"message": "OAuth configuration saved successfully."})
            else:
                self._send_response(500, {"error": "Failed to save OAuth configuration to file."})
            return
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
    load_class_data_from_sql() # Load class data
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
    print(f"Using classes data file: {CLASSES_SQL_FILE_PATH}")
    print(f"Using Google client secrets file: {CLIENT_SECRETS_FILE}")
    print(f"Using hashlib.pbkdf2_hmac with {ITERATIONS} iterations.")
    print(f"\nAccess the application via: http://{HOST}:{PORT}/")
    print(f"(Will redirect to /login.html if not logged in)")
    print("-------------------------------------------------------------")
    print("")


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
