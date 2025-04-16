import webbrowser
import os
import json
import re  # Import regular expressions for parsing
import io
from http.server import SimpleHTTPRequestHandler, HTTPServer

BACKEND = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BACKEND, '../frontend')
DATA_DIR = os.path.join(BACKEND, 'data')
COUNTS_SQL_FILE = os.path.join(DATA_DIR, 'tables.sql') # File for counts data
LOGINS_SQL_FILE = os.path.join(DATA_DIR, 'logins.sql') # File for login data

os.makedirs(DATA_DIR, exist_ok=True)

# --- Function to parse logins.sql ---
def load_users_from_sql(sql_file_path):
    """
    Parses the logins.sql file to extract usernames and placeholder password hashes.
    WARNING: This is a fragile parsing method and relies on the specific format
             of the INSERT statements in the provided logins.sql file.
             It does NOT execute SQL.
    Returns:
        dict: A dictionary mapping username -> placeholder_hash
    """
    users = {}
    # Regex to find INSERT lines and capture username and placeholder hash
    # Assumes format like: VALUES ('username', 'placeholder_hash');
    # It's quite specific to the example file's format.
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
                print(f"Loaded user: {username} (placeholder: {placeholder_hash})") # Debug print
    except Exception as e:
        print(f"Error reading or parsing {sql_file_path}: {e}")

    if not users:
        print(f"Warning: No user data successfully parsed from {sql_file_path}")

    return users

# --- INSECURE MAPPING: Placeholder Hash -> Plain Text Password ---
# This mapping is REQUIRED because we cannot verify plain text passwords
# against the placeholder hashes read from the SQL file.
# THIS IS ONLY FOR DEMONSTRATION AND IS HIGHLY INSECURE.
# It maps the exact placeholder strings found in logins.sql to the
# corresponding plain text passwords mentioned in the SQL comments.
PLACEHOLDER_HASH_TO_PASSWORD = {
    'placeholder_hash_for_password123': 'password123',
    'placeholder_hash_for_another_password': 'another_password'
    # Add more mappings here if you add more users to logins.sql
}
# -----------------------------------------------------------------

# --- Load user data on startup ---
USERS_DATA = load_users_from_sql(LOGINS_SQL_FILE)
# ---------------------------------

# --- Functions for counts data (generate_sql, parse_sql) remain the same ---
# (Keep the existing generate_sql and parse_sql functions for counts data here)
def generate_sql(student_counts, teacher_counts):
    # ... (keep existing function)
    values = []
    for points, count in enumerate(student_counts):
        values.append(f"('student', {points}, {count})")
    for points, count in enumerate(teacher_counts):
        values.append(f"('teacher', {points}, {count})")
    # Ensure the file path is correct if you use this function elsewhere
    # For now, it seems unused based on the POST/GET handlers provided
    return "INSERT INTO counts (type, points, count) VALUES\n" + ",\n".join(values) + ";\n"

def parse_sql():
    # ... (keep existing function, ensure it uses COUNTS_SQL_FILE)
    if not os.path.exists(COUNTS_SQL_FILE):
        return [0]*7, [0]*7

    student = [0]*7
    teacher = [0]*7

    try: # Add basic error handling for parsing
        with open(COUNTS_SQL_FILE, 'r') as f:
            lines = f.readlines()

        for line in lines:
            # Improved parsing to be slightly more robust
            if line.strip().startswith("('"):
                try:
                    # Attempt to parse assuming ('type', points, count) format
                    parts = line.strip().strip("(),;").split(',')
                    if len(parts) == 3:
                        typ = parts[0].strip().strip("'")
                        points = int(parts[1].strip())
                        count = int(parts[2].strip())
                        if typ == "student" and 0 <= points < 7:
                            student[points] = count
                        elif typ == "teacher" and 0 <= points < 7:
                            teacher[points] = count
                    else:
                         print(f"Warning: Skipping malformed line in {COUNTS_SQL_FILE}: {line.strip()}")
                except (IndexError, ValueError) as e:
                    print(f"Warning: Could not parse line in {COUNTS_SQL_FILE}: {line.strip()} - Error: {e}")
    except Exception as e:
         print(f"Error reading counts file {COUNTS_SQL_FILE}: {e}")

    return student, teacher
# ------------------------------------------------------------------------


class MyHandler(SimpleHTTPRequestHandler):
    # Serve files relative to FRONTEND_DIR
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_POST(self):
        # --- LOGIN HANDLING ---
        if self.path == '/login':
            try:
                length = int(self.headers.get('Content-Length'))
                body = self.rfile.read(length)
                credentials = json.loads(body)
                username = credentials.get('username')
                submitted_password = credentials.get('password')

                # --- Authentication Logic (Reading SQL, Using Insecure Mapping) ---
                login_successful = False
                if username in USERS_DATA:
                    placeholder_hash = USERS_DATA[username]
                    # Look up the expected plain text password using the insecure mapping
                    expected_password = PLACEHOLDER_HASH_TO_PASSWORD.get(placeholder_hash)

                    if submitted_password == expected_password:
                        login_successful = True
                    else:
                         print(f"Password mismatch for user {username}. Submitted: '{submitted_password}', Expected (via map): '{expected_password}'")

                else:
                    print(f"Username '{username}' not found in data loaded from SQL.")


                if login_successful:
                    # Login successful
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': True, 'message': 'Login successful'}).encode())
                    print(f"Login successful for user: {username}") # Server log
                else:
                    # Login failed
                    self.send_response(401) # Unauthorized
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': False, 'message': 'Invalid username or password'}).encode())
                    print(f"Login failed for user attempt: {username}") # Server log
                # ----------------------------------------------------

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
            try:
                length = int(self.headers.get('Content-Length'))
                body = self.rfile.read(length)
                data = json.loads(body)

                # Use COUNTS_SQL_FILE for saving counts
                with open(COUNTS_SQL_FILE, 'w') as f:
                    f.write("-- Counts data generated by the application --\n") # Add a comment
                    # Optional: Add table creation if it might be missing
                    # f.write("CREATE TABLE IF NOT EXISTS counts (\n")
                    # f.write("    type TEXT,\n")
                    # f.write("    points INTEGER,\n")
                    # f.write("    count INTEGER,\n")
                    # f.write("    PRIMARY KEY (type, points)\n")
                    # f.write(");\n\n")
                    f.write("INSERT INTO counts (type, points, count) VALUES\n")
                    values = []
                    if 'studentCounts' in data:
                         for i, count in enumerate(data['studentCounts']):
                            values.append(f"('student', {i}, {count})")
                    if 'teacherCounts' in data:
                        for i, count in enumerate(data['teacherCounts']):
                            values.append(f"('teacher', {i}, {count})")
                    if values:
                        f.write(',\n'.join(values) + ';')
                    else:
                        f.write("-- No data to save --\n") # Handle empty data case


                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True, 'message': 'Counts saved'}).encode())
                print("Counts data saved.")

            except json.JSONDecodeError:
                 self.send_response(400) # Bad Request
                 self.send_header('Content-Type', 'application/json')
                 self.end_headers()
                 self.wfile.write(json.dumps({'success': False, 'message': 'Invalid JSON format for saving counts'}).encode())
                 print("Error: Invalid JSON received for saving counts.")
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'message': f'Error saving counts: {e}'}).encode())
                print(f"Error saving counts: {e}")
        else:
            # If the path is not recognized for POST, send a 404 or 405
            self.send_error(405, "Method Not Allowed")


    def do_GET(self):
        # --- LOAD COUNTS DATA ---
        if self.path == '/load-sql':
            try:
                # Use the parse_sql function which reads from COUNTS_SQL_FILE
                studentCounts, teacherCounts = parse_sql()

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'studentCounts': studentCounts,
                    'teacherCounts': teacherCounts
                }).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': f"Error loading counts: {e}"}).encode())
                print(f"Error loading counts: {e}")

        # --- SERVE LOGIN PAGE explicitly if requested ---
        # Ensure login.html is served correctly
        elif self.path == '/' or self.path == '/login.html':
             # Let the parent class handle serving login.html from FRONTEND_DIR
             super().do_GET()

        # --- SERVE OTHER FRONTEND FILES ---
        else:
            # Let SimpleHTTPRequestHandler handle serving other files (index.html, style.css, script.js, login.js)
            # from the specified FRONTEND_DIR
            super().do_GET()


def run_server():
    PORT = 8000
    # Start the server
    try:
        # Ensure the handler knows where the frontend files are
        # The directory argument in MyHandler's __init__ handles this.
        with HTTPServer(('localhost', PORT), MyHandler) as server:
            print(f"Serving frontend from: {FRONTEND_DIR}")
            print(f"Backend data directory: {DATA_DIR}")
            print(f"Attempting to load users from: {LOGINS_SQL_FILE}")
            print(f"Loaded {len(USERS_DATA)} user(s) for login check.")
            print(f"Access frontend at http://localhost:{PORT}/login.html")
            # Open the login page specifically
            webbrowser.open(f"http://localhost:{PORT}/login.html")
            server.serve_forever()
    except OSError as e:
        print(f"\nError starting server: {e}")
        print(f"Port {PORT} might already be in use. Try stopping other servers or choosing a different port.")
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    run_server()
