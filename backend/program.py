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

# --- Configuration ---
BACKEND_DIR = Path(__file__).parent.resolve()
FRONTEND_DIR = (BACKEND_DIR.parent / 'frontend').resolve()
DATA_DIR = (BACKEND_DIR / 'data').resolve()
SQL_FILE_PATH = DATA_DIR / 'tables.sql' # Path to the SQL data file
HOST = 'localhost'
PORT = 8000
SUPPORTED_CLASSES = ['C1', 'C2', 'C3'] # Must match menu.html

# --- In-Memory Data Store and Lock ---
# Use defaultdict for easier handling of missing keys
# Structure: data_store[class_name][type][points] = count
data_store = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
data_lock = threading.Lock() # Lock to protect file access and in-memory data modification

# --- SQL File Handling Functions ---

def parse_sql_line(line):
    """Parses a single INSERT statement line."""
    # Regex to capture class_name, type, points, count from the specific INSERT format
    # Handles single quotes around class_name and type
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
        # Handle the old format for potential backward compatibility or ignore
        match_old = re.match(
             r"INSERT INTO counts \(type, points, count\) VALUES \('([^']*)', (\d+), (\d+)\);",
             line.strip()
        )
        if match_old:
            print(f"Warning: Ignoring old format line (missing class_name): {line.strip()}")
        elif line.strip() and not line.strip().startswith('--'):
             print(f"Warning: Could not parse line: {line.strip()}")
        return None


def load_data_from_sql():
    """Loads data from tables.sql into the in-memory data_store."""
    global data_store
    print(f"Attempting to load data from: {SQL_FILE_PATH}")
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp_data = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
    found_classes = set()

    if SQL_FILE_PATH.exists():
        try:
            with open(SQL_FILE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    parsed = parse_sql_line(line)
                    if parsed:
                        class_name, type_val, points, count = parsed
                        if 0 <= points <= 6 and type_val in ['student', 'teacher']:
                             temp_data[class_name][type_val][points] = count
                             found_classes.add(class_name)
                        else:
                             print(f"Warning: Invalid data skipped in line: {line.strip()}")

            print(f"Loaded data for classes: {', '.join(sorted(list(found_classes)))}")

        except FileNotFoundError:
            print(f"Warning: {SQL_FILE_PATH} not found.") # Should be handled by exists() check, but belt-and-suspenders
            pass # Will proceed to initialize defaults
        except Exception as e:
            print(f"Error reading or parsing {SQL_FILE_PATH}: {e}. Will attempt to initialize defaults.")
            temp_data.clear() # Clear potentially corrupt data
            found_classes.clear()

    # Ensure all SUPPORTED_CLASSES have default entries if missing from file or if file was empty/corrupt
    needs_save = False
    for class_name in SUPPORTED_CLASSES:
        if class_name not in temp_data:
             print(f"Initializing default data for missing class: {class_name}")
             needs_save = True # Need to save the defaults we're adding
             for type_val in ['student', 'teacher']:
                 for points_val in range(7): # 0 to 6
                     temp_data[class_name][type_val][points_val] = 0 # Default to 0

    # Atomically update the global data store (though atomicity isn't strictly needed here)
    with data_lock:
        data_store = temp_data

    # If we added defaults because the file was missing or incomplete, save it now
    if needs_save or not SQL_FILE_PATH.exists():
        print("Saving initial/default data to tables.sql...")
        save_data_to_sql() # This will acquire the lock again internally

    print("Data loading/initialization complete.")


def save_data_to_sql():
    """Saves the current in-memory data_store back to tables.sql."""
    global data_store
    print(f"Attempting to save data to: {SQL_FILE_PATH}")
    # Acquire lock to prevent concurrent writes and reads during write
    with data_lock:
        try:
            sql_lines = []
            sql_lines.append(f"-- Data saved on {datetime.datetime.now().isoformat()} --")
            sql_lines.append("-- This file is used as the primary data storage. --")
            sql_lines.append("")

            # Iterate through the in-memory store and generate INSERT statements
            # Sort for consistent file output
            for class_name in sorted(data_store.keys()):
                 # Only save classes we know about or that are supported
                 # (Prevents saving potentially temporary/erroneous class data)
                 # if class_name not in SUPPORTED_CLASSES and class_name not in loaded_classes_at_start:
                 #    continue # Or decide if you want to save dynamically added classes

                 for type_val in sorted(data_store[class_name].keys()):
                     for points_val in sorted(data_store[class_name][type_val].keys()):
                         count_val = data_store[class_name][type_val][points_val]
                         # Escape single quotes in class_name (though unlikely needed)
                         safe_class_name = class_name.replace("'", "''")
                         insert_statement = f"INSERT INTO counts (class_name, type, points, count) VALUES ('{safe_class_name}', '{type_val}', {points_val}, {count_val});"
                         sql_lines.append(insert_statement)

            # Write the file (overwrite existing)
            with open(SQL_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write("\n".join(sql_lines))
                f.write("\n") # Add a final newline
            print(f"Data successfully saved to {SQL_FILE_PATH}")
            return True

        except IOError as e:
            print(f"Error writing to {SQL_FILE_PATH}: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred during save: {e}")
            return False


# --- HTTP Request Handler ---

class ColorDaysHandler(http.server.BaseHTTPRequestHandler):

    # _send_response and do_OPTIONS remain the same as before...
    # Helper to send JSON responses with CORS headers
    def _send_response(self, status_code, data=None, content_type='application/json', headers=None):
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        # --- CORS Headers ---
        self.send_header('Access-Control-Allow-Origin', '*') # Allow requests from any origin (adjust for production)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        # --- End CORS ---
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        self.end_headers()
        if data is not None:
            response_body = json.dumps(data).encode('utf-8') if content_type == 'application/json' else data
            self.wfile.write(response_body)

    # Handle CORS preflight requests
    def do_OPTIONS(self):
        self._send_response(204, data=None) # No Content for OPTIONS


    # Handle GET requests (serving files and /api/counts)
    def do_GET(self):
        global data_store # Access the in-memory data
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)

        # API Endpoint: /api/counts?class=ClassName
        if path == '/api/counts':
            class_name = query.get('class', [None])[0]
            if not class_name:
                self._send_response(400, {"error": "Missing 'class' query parameter"})
                return

            # Read from the in-memory data store (no lock needed for read if writes are locked)
            # Although, acquiring lock ensures we don't read while a save is half-done
            with data_lock:
                if class_name in data_store:
                    class_data = data_store[class_name]
                    # Format data for JSON response
                    response_data = []
                    for type_val in sorted(class_data.keys()):
                        for points_val in sorted(class_data[type_val].keys()):
                            response_data.append({
                                "type": type_val,
                                "points": points_val,
                                "count": class_data[type_val][points_val]
                            })
                    self._send_response(200, response_data)
                else:
                    # Class not found in memory (might happen if SUPPORTED_CLASSES changed)
                    print(f"Warning: Class '{class_name}' requested but not found in memory.")
                    self._send_response(200, []) # Return empty list for consistency
            return

        # File Serving Logic (remains the same as before)...
        try:
            if path == '/':
                file_path = FRONTEND_DIR / 'menu.html'
            else:
                safe_subpath = path.lstrip('/')
                file_path = (FRONTEND_DIR / safe_subpath).resolve()
                if not file_path.is_relative_to(FRONTEND_DIR):
                     raise FileNotFoundError("Attempted path traversal")

            if file_path.is_file():
                content_type = 'text/html'
                if file_path.suffix == '.css': content_type = 'text/css'
                elif file_path.suffix == '.js': content_type = 'application/javascript'
                elif file_path.suffix == '.json': content_type = 'application/json'

                with open(file_path, 'rb') as f: content = f.read()
                self._send_response(200, data=content, content_type=content_type)
            else:
                raise FileNotFoundError(f"File not found: {file_path}")

        except FileNotFoundError as e:
            print(f"File not found error: {e}")
            self._send_response(404, {"error": "File not found"}, content_type='application/json')
        except Exception as e:
            print(f"Error serving file {path}: {e}")
            self._send_response(500, {"error": "Internal server error serving file"}, content_type='application/json')


    # Handle POST requests (/api/increment, /api/decrement)
    def do_POST(self):
        global data_store # Access the in-memory data
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        # Read request body (same as before)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_response(400, {"error": "Invalid JSON payload"})
            return

        class_name = data.get('className')
        type_val = data.get('type')
        points_val = data.get('points')

        # Basic validation (same as before)
        if not all([class_name, type_val, points_val is not None]):
            self._send_response(400, {"error": "Missing data: className, type, or points"})
            return
        if type_val not in ['student', 'teacher']:
            self._send_response(400, {"error": "Invalid type"})
            return
        if not isinstance(points_val, int) or not (0 <= points_val <= 6):
             self._send_response(400, {"error": "Invalid points value"})
             return

        # --- Critical Section: Modify in-memory data and save to file ---
        success = False
        message = "Operation failed"
        status_code = 500 # Default to internal error

        with data_lock: # Acquire lock before modifying data or saving
            try:
                # Check if class/type/points exists (using defaultdict avoids KeyError)
                current_count = data_store[class_name][type_val][points_val]

                if path == '/api/increment':
                    # Increment in memory
                    data_store[class_name][type_val][points_val] = current_count + 1
                    # Save the entire data store back to the file
                    if save_data_to_sql():
                        success = True
                        message = "Count incremented"
                        status_code = 200
                    else:
                        # Rollback memory change if save failed? Difficult with flat file.
                        # For simplicity, we leave memory changed but report error.
                        message = "Count incremented in memory, but failed to save to file."
                        status_code = 500 # Internal Server Error

                elif path == '/api/decrement':
                    if current_count > 0:
                        # Decrement in memory
                        data_store[class_name][type_val][points_val] = current_count - 1
                        # Save the entire data store back to the file
                        if save_data_to_sql():
                            success = True
                            message = "Count decremented"
                            status_code = 200
                        else:
                            message = "Count decremented in memory, but failed to save to file."
                            status_code = 500
                    else:
                        # Count is already zero, do nothing to file
                        success = False # Operation didn't change state
                        message = "Count already zero"
                        status_code = 400 # Bad Request

                else:
                    # Endpoint not found
                    success = False
                    message = "API endpoint not found"
                    status_code = 404

            except Exception as e:
                print(f"Error during POST {path} operation: {e}")
                success = False
                message = "An internal error occurred during the operation."
                status_code = 500
        # --- End Critical Section ---

        # Send response outside the lock
        if status_code == 200:
             self._send_response(status_code, {"success": success, "message": message})
        else:
             self._send_response(status_code, {"error": message})


# --- Main Execution ---
if __name__ == "__main__":
    # Load initial data from SQL file (or create/initialize if needed)
    load_data_from_sql()

    # Server setup (remains the same)
    class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        pass

    httpd = ThreadingHTTPServer((HOST, PORT), ColorDaysHandler)

    print(f"Serving HTTP on {HOST}:{PORT}...")
    print(f"Using data file: {SQL_FILE_PATH}")
    print(f"Access the application via: http://{HOST}:{PORT}/menu.html")

    try:
        # webbrowser.open(f"http://localhost:{PORT}/menu.html") # Open menu page
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopping...")
        # Attempt a final save on shutdown? Risky if shutdown is abrupt.
        # print("Attempting final data save...")
        # save_data_to_sql()
        httpd.shutdown()
        httpd.server_close()
        print("Server stopped.")

