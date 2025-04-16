import webbrowser
import os
import json
import re
import io
from http.server import SimpleHTTPRequestHandler, HTTPServer
from http.cookies import SimpleCookie # Import SimpleCookie for easier cookie handling

BACKEND = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BACKEND, '../frontend')
DATA_DIR = os.path.join(BACKEND, 'data')
COUNTS_SQL_FILE = os.path.join(DATA_DIR, 'tables.sql')
LOGINS_SQL_FILE = os.path.join(DATA_DIR, 'logins.sql')

os.makedirs(DATA_DIR, exist_ok=True)

# --- Function to parse logins.sql (remains the same) ---
def load_users_from_sql(sql_file_path):
    users = {}
    insert_pattern = re.compile(
        r"INSERT\s+INTO\s+users\s+\(username,\s*password_hash\)\s+"
        r"VALUES\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\);",
        re.IGNORECASE
    )
    if not os.path.exists(sql_file_path):
        print(f"Warning: Login SQL file not found at {sql_file_path}")
        return {}
    try:
        with open(sql_file_path, 'r') as f:
            content = f.read()
            matches = insert_pattern.findall(content)
            for username, placeholder_hash in matches:
                users[username] = placeholder_hash
                # print(f"Loaded user: {username} (placeholder: {placeholder_hash})") # Keep commented unless debugging
    except Exception as e:
        print(f"Error reading or parsing {sql_file_path}: {e}")
    if not users:
        print(f"Warning: No user data successfully parsed from {sql_file_path}")
    return users

# --- INSECURE MAPPING (remains the same) ---
PLACEHOLDER_HASH_TO_PASSWORD = {
    'placeholder_hash_for_password123': 'password123',
    'placeholder_hash_for_another_password': 'another_password'
}

# --- Load user data on startup (remains the same) ---
USERS_DATA = load_users_from_sql(LOGINS_SQL_FILE)

# --- Functions for counts data (generate_sql, parse_sql) remain the same ---
def generate_sql(student_counts, teacher_counts):
    # ... (keep existing function)
    values = []
    for points, count in enumerate(student_counts):
        values.append(f"('student', {points}, {count})")
    for points, count in enumerate(teacher_counts):
        values.append(f"('teacher', {points}, {count})")
    return "INSERT INTO counts (type, points, count) VALUES\n" + ",\n".join(values) + ";\n"

def parse_sql():
    # ... (keep existing function)
    if not os.path.exists(COUNTS_SQL_FILE):
        return [0]*7, [0]*7
    student = [0]*7
    teacher = [0]*7
    try:
        with open(COUNTS_SQL_FILE, 'r') as f: lines = f.readlines()
        for line in lines:
            if line.strip().startswith("('"):
                try:
                    parts = line.strip().strip("(),;").split(',')
                    if len(parts) == 3:
                        typ, points_str, count_str = parts
                        typ = typ.strip().strip("'")
                        points = int(points_str.strip())
                        count = int(count_str.strip())
                        if typ == "student" and 0 <= points < 7: student[points] = count
                        elif typ == "teacher" and 0 <= points < 7: teacher[points] = count
                    else: print(f"Warning: Skipping malformed line in {COUNTS_SQL_FILE}: {line.strip()}")
                except (IndexError, ValueError) as e: print(f"Warning: Could not parse line in {COUNTS_SQL_FILE}: {line.strip()} - Error: {e}")
    except Exception as e: print(f"Error reading counts file {COUNTS_SQL_FILE}: {e}")
    return student, teacher
# ------------------------------------------------------------------------

# --- Simple Session Token (replace with something secure in real apps) ---
SESSION_COOKIE_NAME = "color_days_session"
VALID_SESSION_VALUE = "user_is_logged_in_12345" # Basic value, not secure
# ------------------------------------------------------------------------

class MyHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    # --- Helper to get cookies from request ---
    def get_cookies(self):
        """Parses cookies from the 'Cookie' header."""
        cookies = SimpleCookie()
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            cookies.load(cookie_header)
        return cookies

    def do_POST(self):
        # --- LOGIN HANDLING ---
        if self.path == '/login':
            # ... (login logic remains the same - sets cookie on success) ...
            try:
                length = int(self.headers.get('Content-Length'))
                body = self.rfile.read(length)
                credentials = json.loads(body)
                username = credentials.get('username')
                submitted_password = credentials.get('password')

                login_successful = False
                if username in USERS_DATA:
                    placeholder_hash = USERS_DATA[username]
                    expected_password = PLACEHOLDER_HASH_TO_PASSWORD.get(placeholder_hash)
                    if expected_password and submitted_password == expected_password:
                        login_successful = True

                if login_successful:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    # *** SET THE SESSION COOKIE on successful login ***
                    cookie = SimpleCookie()
                    cookie[SESSION_COOKIE_NAME] = VALID_SESSION_VALUE
                    cookie[SESSION_COOKIE_NAME]['path'] = '/' # Make cookie valid for all paths
                    # Optional security attributes (recommended):
                    # cookie[SESSION_COOKIE_NAME]['httponly'] = True # Prevents JS access
                    # cookie[SESSION_COOKIE_NAME]['samesite'] = 'Lax' # CSRF protection
                    self.send_header('Set-Cookie', cookie.output(header='').strip())
                    # **************************************************
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': True, 'message': 'Login successful'}).encode())
                    print(f"Login successful for user: {username}, session cookie set.")
                else:
                    self.send_response(401) # Unauthorized
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': False, 'message': 'Invalid username or password'}).encode())
                    print(f"Login failed for user attempt: {username}")

            except json.JSONDecodeError:
                 self.send_response(400) # Bad Request
                 self.send_header('Content-Type', 'application/json')
                 self.end_headers()
                 self.wfile.write(json.dumps({'success': False, 'message': 'Invalid JSON format in request body'}).encode())
                 print("Error: Invalid JSON received for login.")
            except Exception as e:
                self.send_response(500) # Internal Server Error
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'message': f'Server error during login: {e}'}).encode())
                print(f"Error during login processing: {e}")

        # --- SAVE COUNTS DATA ---
        elif self.path == '/save-sql':
            # *** ADD AUTHENTICATION CHECK HERE ***
            cookies = self.get_cookies()
            is_logged_in = cookies.get(SESSION_COOKIE_NAME) and \
                           cookies[SESSION_COOKIE_NAME].value == VALID_SESSION_VALUE

            if not is_logged_in:
                print(f"Denied POST request to /save-sql - User not logged in.")
                self.send_response(401) # Unauthorized
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'message': 'Authentication required'}).encode())
                return # Stop processing if not logged in
            # **************************************

            # --- Proceed with saving only if logged in ---
            try:
                print("Processing authenticated POST request to /save-sql...") # Log access
                length = int(self.headers.get('Content-Length'))
                body = self.rfile.read(length)
                data = json.loads(body)
                with open(COUNTS_SQL_FILE, 'w') as f:
                    f.write("-- Counts data generated by the application --\n")
                    f.write("INSERT INTO counts (type, points, count) VALUES\n")
                    values = []
                    if 'studentCounts' in data:
                         for i, count in enumerate(data['studentCounts']): values.append(f"('student', {i}, {count})")
                    if 'teacherCounts' in data:
                        for i, count in enumerate(data['teacherCounts']): values.append(f"('teacher', {i}, {count})")
                    if values: f.write(',\n'.join(values) + ';')
                    else: f.write("-- No data to save --\n")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True, 'message': 'Counts saved'}).encode())
                print("Counts data saved successfully.")
            except json.JSONDecodeError:
                 self.send_response(400); self.send_header('Content-Type', 'application/json'); self.end_headers()
                 self.wfile.write(json.dumps({'success': False, 'message': 'Invalid JSON format for saving counts'}).encode())
                 print("Error: Invalid JSON received for saving counts.")
            except Exception as e:
                self.send_response(500); self.send_header('Content-Type', 'application/json'); self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'message': f'Error saving counts: {e}'}).encode())
                print(f"Error saving counts: {e}")
        else:
            # Handle other POST requests if any, or send error
            self.send_error(405, "Method Not Allowed")


    def do_GET(self):
        # ... (do_GET remains the same as before, already protects relevant GET endpoints) ...
        cookies = self.get_cookies()
        is_logged_in = cookies.get(SESSION_COOKIE_NAME) and \
                       cookies[SESSION_COOKIE_NAME].value == VALID_SESSION_VALUE

        # --- PROTECT index.html and root path ---
        if self.path == '/' or self.path == '/index.html':
            if is_logged_in:
                print(f"Serving protected path '{self.path}' - User logged in.")
                if self.path == '/': self.path = '/index.html'
                super().do_GET()
            else:
                print(f"Redirecting request for '{self.path}' to login - User not logged in.")
                self.send_response(302); self.send_header('Location', '/login.html'); self.end_headers()
            return
        # --- Allow access to login page and its resources ---
        if self.path == '/login.html' or self.path == '/login.js' or self.path == '/style.css':
             print(f"Serving public resource: {self.path}")
             super().do_GET()
             return
        # --- LOAD COUNTS DATA (only if logged in) ---
        if self.path == '/load-sql':
            if is_logged_in:
                try:
                    studentCounts, teacherCounts = parse_sql()
                    self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
                    self.wfile.write(json.dumps({'studentCounts': studentCounts, 'teacherCounts': teacherCounts}).encode())
                except Exception as e:
                    self.send_response(500); self.send_header('Content-Type', 'application/json'); self.end_headers()
                    self.wfile.write(json.dumps({'error': f"Error loading counts: {e}"}).encode())
                    print(f"Error loading counts: {e}")
            else:
                print(f"Denied access to /load-sql - User not logged in.")
                self.send_response(401); self.send_header('Content-Type', 'application/json'); self.end_headers()
                self.wfile.write(json.dumps({'error': 'Authentication required'}).encode())
            return
        # --- Handle other frontend files (e.g., script.js for index.html) ---
        if self.path == '/script.js':
             if is_logged_in:
                 print(f"Serving protected resource: {self.path}")
                 super().do_GET()
             else:
                 print(f"Denied access to {self.path} - User not logged in.")
                 self.send_error(401, "Unauthorized")
             return
        # --- Default ---
        print(f"Serving potentially unprotected resource via default handler: {self.path}")
        super().do_GET()


def run_server():
    # ... (run_server remains the same) ...
    PORT = 8000
    try:
        with HTTPServer(('localhost', PORT), MyHandler) as server:
            print(f"Serving frontend from: {FRONTEND_DIR}")
            print(f"Backend data directory: {DATA_DIR}")
            print(f"Attempting to load users from: {LOGINS_SQL_FILE}")
            print(f"Loaded {len(USERS_DATA)} user(s) for login check.")
            print(f"Access frontend at http://localhost:{PORT}/login.html") # Start at login
            webbrowser.open(f"http://localhost:{PORT}/login.html") # Open login page
            server.serve_forever()
    except OSError as e:
        print(f"\nError starting server: {e}")
        print(f"Port {PORT} might already be in use.")
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    run_server()
