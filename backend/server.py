import http.server
import socketserver
import json
import urllib.parse
from http.cookies import SimpleCookie
import os
import traceback
import collections

try:
    from google_auth_oauthlib.flow import InstalledAppFlow as IAF
    from googleapiclient import discovery as discovery_module
    
    # Assign to our module-level variables
    InstalledAppFlow = IAF
    google_discovery_service = discovery_module
    print("Google OAuth libraries found and imported.")
except ImportError:
    print("One or more Google OAuth libraries not found, attempting to install...")
    install_cmd = 'pip3 install --upgrade google-auth-oauthlib google-api-python-client requests'
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

from config import *
from utils import (
    generate_random_code,
    hash_password,
    verify_password,
    create_cookies,
    create_cookie_clear_headers,
    generate_token,
    store_token,
)
from auth import get_current_user_info, is_user_using_oauth
from data_manager import (
    save_counts_to_db,
    load_counts_from_db,
    load_class_data_from_db,
    save_class_data_to_db,
    load_students_data_from_db,
    save_students_data_to_db,
    load_user_data_from_db,
    save_user_data_to_db,
    load_main_config_from_json,
    is_student_allowed,
    user_password_store,
    class_data_store,
    students_data_store,
    data_lock,
    get_db_connection,
)

from api.get import GET_ROUTES
from api.post import POST_ROUTES

class ColorDaysHandler(http.server.BaseHTTPRequestHandler):
    active_sessions = {}

    def get_cookies(self):
        cookies = SimpleCookie()
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            cookies.load(cookie_header)
        return cookies

    def is_logged_in(self):
        cookies = self.get_cookies()
        session_cookie = cookies.get(SESSION_COOKIE_NAME)
        if session_cookie and session_cookie.value in self.active_sessions:
            return True
        return False

    def _send_response(self, status_code, data=None, content_type='application/json', headers=None):
        try:
            self.send_response(status_code)
            self.send_header('Content-type', content_type)
            # Get the origin from the request, or use localhost as fallback
            origin = self.headers.get('Origin', 'http://localhost:8000')
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
            self.send_header('Access-Control-Allow-Credentials', 'true')
            if headers:
                for key, value in headers.items():
                    self.send_header(key, value)
            self.end_headers()
            if data is not None:
                if content_type == 'application/json':
                    if isinstance(data, bytes):
                        response_body = data
                    else:
                        response_body = json.dumps(data).encode('utf-8')
                else:
                    response_body = data
                self.wfile.write(response_body)
        except Exception as e:
            print(f"!!! Error sending response (status {status_code}): {e}")

    def send_json(self, data, status=200):
        response = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_OPTIONS(self):
        self._send_response(204)

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)

        handler = GET_ROUTES.get(path)
        if handler:
            handler(self)
            return

        is_logged_in_flag = self.is_logged_in()
        cookies = self.get_cookies()
        password_change_required = cookies.get(CHANGE_PASSWORD_COOKIE_NAME)

        allowed_get_paths_during_change = ['/login.html', '/change-password.html', '/logout', '/change-password.js', '/style.css']

        if is_logged_in_flag and password_change_required and path.startswith('/api/') and path not in allowed_get_paths_during_change:
            self._send_response(403, {"error": "Password change required before accessing this API resource."})
            return

        if is_logged_in_flag and password_change_required and path not in allowed_get_paths_during_change and not path.startswith('/api/'):
            self.send_response(302)
            self.send_header('Location', '/change-password.html')
            self.end_headers()
            return

        # Protected pages that require authentication
        protected_pages = ['/menu.html', '/index.html', '/classes.html', '/config.html', '/students.html', '/change-password.html']

        if path in protected_pages or path == '/':
            if not is_logged_in_flag:
                # Redirect to login if not authenticated
                self.send_response(302)
                self.send_header('Location', '/login.html')
                self.end_headers()
                return

        # Additional check for admin/teacher-only pages
        if path == '/classes.html' or path == '/config.html':
            cookies = self.get_cookies()
            if cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME):
                self._send_response(403, {"error": "Forbidden: Access to this page is restricted for your account type."})
                return

        # File serving logic
        if path == '/':
            path = '/index.html'
        
        file_path = FRONTEND_DIR / path.lstrip('/')
        
        if file_path.is_file():
            content_type = self.guess_content_type(file_path)
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                self._send_response(200, content, content_type)
            except IOError:
                self._send_response(500, b'Error reading file')
        else:
            self._send_response(404, b'File not found')

    def guess_content_type(self, file_path):
        if file_path.suffix == '.html':
            return 'text/html'
        elif file_path.suffix == '.css':
            return 'text/css'
        elif file_path.suffix == '.js':
            return 'application/javascript'
        elif file_path.suffix == '.json':
            return 'application/json'
        else:
            return 'application/octet-stream'

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        handler = POST_ROUTES.get(path)
        if handler:
            # Routes that read their own request body (don't pre-read the body for these)
            if path in ['/login', '/login/student', '/logout']:
                try:
                    handler(self)
                    return
                except Exception as e:
                    print(f"Error during {path} processing: {e}")
                    traceback.print_exc()
                    self._send_response(500, {"error": f"Server error during {path}"})
                    return

            # For all other routes, read and parse the body
            content_length = int(self.headers.get('Content-Length', 0))
            post_body_bytes = b''
            if content_length > 0:
                post_body_bytes = self.rfile.read(content_length)
            
            # All other routes expect a JSON body and 'data' argument
            if not post_body_bytes:
                self._send_response(400, {"error": "Missing JSON payload for this endpoint"})
                return
            try:
                data = json.loads(post_body_bytes)
                handler(self, data) # Call with 'self' and 'data'
            except json.JSONDecodeError:
                self._send_response(400, {"error": "Invalid JSON payload"})
        else:
            self._send_response(404, {"error": "API endpoint not found"})
