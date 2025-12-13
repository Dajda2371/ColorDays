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

def handle_increment_module(handler_instance, data, request_path):
    """Handle incrementing a count value."""
    class_name = data.get('className')
    type_val = data.get('type')
    points_val = data.get('points')
    day_identifier = data.get('day')

    # Basic validation
    if not all([class_name, type_val, points_val is not None, day_identifier]):
        handler_instance._send_response(400, {"error": "Missing data: className, type, points, or day"})
        return
    if type_val not in ['student', 'teacher']:
        handler_instance._send_response(400, {"error": "Invalid type"})
        return
    if not isinstance(points_val, int) or not (0 <= points_val <= 6):
        handler_instance._send_response(400, {"error": "Invalid points value"})
        return
    if day_identifier.lower() not in ['monday', 'tuesday', 'wednesday']:
        handler_instance._send_response(400, {"error": f"Invalid day. Must be one of monday, tuesday, wednesday"})
        return

    # Student Authorization Check
    cookies = handler_instance.get_cookies()
    student_auth_cookie = cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
    if student_auth_cookie:
        student_code = student_auth_cookie.value
        if not is_student_allowed(student_code, class_name, day_identifier.lower()):
            handler_instance._send_response(403, {"error": "Forbidden: You are not authorized to modify counts for this class/day."})
            return

    try:
        day_specific_data = load_counts_from_db(day_identifier.lower())

        # Initialize if needed
        if class_name not in day_specific_data:
            day_specific_data[class_name] = collections.defaultdict(lambda: collections.defaultdict(int))
            for t in ['student', 'teacher']:
                for p in range(7):
                    day_specific_data[class_name][t][p] = 0

        # Increment
        current_count = day_specific_data[class_name][type_val][points_val]
        day_specific_data[class_name][type_val][points_val] = current_count + 1

        # Save
        if save_counts_to_db(day_identifier.lower(), day_specific_data):
            handler_instance._send_response(200, {"success": True, "message": f"Count incremented for {day_identifier}"})
        else:
            handler_instance._send_response(500, {"error": "Failed to save to database"})
    except Exception as e:
        print(f"Error during increment: {e}")
        traceback.print_exc()
        handler_instance._send_response(500, {"error": "Internal server error"})

def handle_decrement_module(handler_instance, data, request_path):
    """Handle decrementing a count value."""
    class_name = data.get('className')
    type_val = data.get('type')
    points_val = data.get('points')
    day_identifier = data.get('day')

    # Basic validation
    if not all([class_name, type_val, points_val is not None, day_identifier]):
        handler_instance._send_response(400, {"error": "Missing data: className, type, points, or day"})
        return
    if type_val not in ['student', 'teacher']:
        handler_instance._send_response(400, {"error": "Invalid type"})
        return
    if not isinstance(points_val, int) or not (0 <= points_val <= 6):
        handler_instance._send_response(400, {"error": "Invalid points value"})
        return
    if day_identifier.lower() not in ['monday', 'tuesday', 'wednesday']:
        handler_instance._send_response(400, {"error": f"Invalid day. Must be one of monday, tuesday, wednesday"})
        return

    # Student Authorization Check
    cookies = handler_instance.get_cookies()
    student_auth_cookie = cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
    if student_auth_cookie:
        student_code = student_auth_cookie.value
        if not is_student_allowed(student_code, class_name, day_identifier.lower()):
            handler_instance._send_response(403, {"error": "Forbidden: You are not authorized to modify counts for this class/day."})
            return

    try:
        day_specific_data = load_counts_from_db(day_identifier.lower())

        # Initialize if needed
        if class_name not in day_specific_data:
            day_specific_data[class_name] = collections.defaultdict(lambda: collections.defaultdict(int))
            for t in ['student', 'teacher']:
                for p in range(7):
                    day_specific_data[class_name][t][p] = 0

        # Decrement (don't go below 0)
        current_count = day_specific_data[class_name][type_val][points_val]
        day_specific_data[class_name][type_val][points_val] = max(0, current_count - 1)

        # Save
        if save_counts_to_db(day_identifier.lower(), day_specific_data):
            handler_instance._send_response(200, {"success": True, "message": f"Count decremented for {day_identifier}"})
        else:
            handler_instance._send_response(500, {"error": "Failed to save to database"})
    except Exception as e:
        print(f"Error during decrement: {e}")
        traceback.print_exc()
        handler_instance._send_response(500, {"error": "Internal server error"})

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
            self.send_header('Access-Control-Allow-Origin', '*')
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

    def handle_get_users(self):
        _user_key, user_role = get_current_user_info(self)
        if not self.is_logged_in() or user_role != ADMIN_ROLE:
            self._send_response(403, {"error": "Forbidden: Administrator access required."})
            return

        user_list = []
        with data_lock:
            for username_key, user_data_val in user_password_store.items():
                password_hash = user_data_val['password_hash']
                role = user_data_val.get('role', DEFAULT_ROLE_FOR_NEW_USERS)
                status = "set"
                if password_hash is None or password_hash.upper() == '_NULL_':
                    status = "not_set"
                elif password_hash == '_GOOGLE_AUTH_USER_':
                    status = "google_auth_user"
                elif password_hash.startswith('_') and password_hash.endswith('_') and \
                     password_hash.upper() != '_NULL_' and password_hash.upper() != '_GOOGLE_AUTH_USER_':
                    status = password_hash[1:-1]
                
                user_list.append({
                    "username": username_key,
                    "password": status,
                    "role": role
                })
        self.send_json(user_list)

    def handle_post_users(self):
        global user_password_store

        if not self.is_logged_in():
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

            user_password_store[username] = {
                'password_hash': 'NOT_SET',
                'profile_picture_url': '_NULL_',
                'role': DEFAULT_ROLE_FOR_NEW_USERS
            }

            success = save_user_data_to_db()

            if success:
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

    def handle_remove_user(self, data):
        username = data.get("username")

        if not username:
            self._send_response(400, {"error": "Missing username"})
            return
                    
        _user_key, current_user_role = get_current_user_info(self)
        if not self.is_logged_in() or current_user_role != ADMIN_ROLE:
            self._send_response(403, {"error": "Forbidden: Administrator access required."})
            return

        if username == 'admin':
            self._send_response(403, {"error": "Cannot remove the admin user."})
            return

        success = False
        message = "Failed to remove user."
        status_code = 500
        save_needed = False

        with data_lock:
            if username not in user_password_store:
                found_user_case_insensitive = next((k for k in user_password_store if k.lower() == username.lower()), None)
                if found_user_case_insensitive:
                    message = f"User '{username}' not found (case mismatch? Found: '{found_user_case_insensitive}')."
                else:
                    message = f"User '{username}' not found."
                status_code = 404
            else:
                del user_password_store[username]
                save_needed = True

            if save_needed:
                if save_user_data_to_db():
                    success = True
                    message = f"User '{username}' removed successfully."
                    status_code = 200
                else:
                    message = f"User '{username}' removed from memory, but FAILED to save to file."
                    status_code = 500

        if success:
            self._send_response(status_code, {"success": True, "message": message})
        else:
            self._send_response(status_code, {"error": message})

    def handle_reset_password(self, data):
        username = data.get("username")
        new_password = data.get("new_password")

        if is_user_using_oauth(username):
            self._send_response(403, {"error": "Password change not allowed for Google OAuth users."})
            return

        if not username or not new_password:
            self._send_response(400, {"error": "Missing username or new_password"})
            return

        hashed = f"_{new_password}_"

        success = False
        message = "Failed to set password."
        status_code = 500
        save_needed = False

        with data_lock:
            if username not in user_password_store:
                message = f"User '{username}' not found."
                status_code = 404
            else:
                try:
                    user_password_store[username]['password_hash'] = hashed
                    save_needed = True
                except Exception as e:
                    message = "Server error during password hashing."
                    status_code = 500

            if save_needed:
                if save_user_data_to_db():
                    success = True
                    message = f"Password for user '{username}' set/reset successfully."
                    status_code = 200
                else:
                    message = f"Password set/reset in memory for '{username}', but FAILED to save to file."
                    status_code = 500

        if success:
            self._send_response(status_code, {"success": True, "message": message})
        else:
            self._send_response(status_code, {"error": message})

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)

        user_key, user_role = get_current_user_info(self)

        if path == '/list_users':
            if not self.is_logged_in():
                self._send_response(401, {"error": "Authentication required"})
                return
            if user_role != ADMIN_ROLE:
                self._send_response(403, {"error": "Forbidden: Administrator access required."})
                return

            with data_lock:
                user_list = sorted(list(user_password_store.keys()))

            self._send_response(200, user_list)
            return

        is_logged_in_flag = self.is_logged_in()
        cookies = self.get_cookies()
        password_change_required = cookies.get(CHANGE_PASSWORD_COOKIE_NAME)

        allowed_get_paths_during_change = ['/login.html', '/change-password.html', '/logout', '/change-password.js', '/style.css']

        if is_logged_in_flag and password_change_required and path.startswith('/api/') and path not in allowed_get_paths_during_change:
            self._send_response(403, {"error": "Password change required before accessing this API resource."})
            return

        if path == '/api/users':
            if not self.is_logged_in():
                self._send_response(401, {"error": "Authentication required"})
                return
            
            self.handle_get_users()
            return

        if path == '/api/classes':
            if not self.is_logged_in():
                self._send_response(401, {"error": "Authentication required"})
                return
        
            is_student_session = cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME) is not None

            if not (user_role in [ADMIN_ROLE, TEACHER_ROLE] or is_student_session):
                self._send_response(403, {"error": "Forbidden: Access to this resource is restricted for your account type."})
                return
            
            with data_lock:
                response_data = list(class_data_store) 
            self._send_response(200, response_data)
            return

        if path == '/api/students':
            if not self.is_logged_in():
                self._send_response(401, {"error": "Authentication required"})
                return
            
            student_auth_cookie = cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
            is_student_user_session = student_auth_cookie is not None
            
            response_payload = []
            with data_lock:
                if is_student_user_session:
                    student_code_from_cookie = student_auth_cookie.value
                    found_student_data_item = None
                    for s_data_item in students_data_store:
                        if s_data_item.get('code') == student_code_from_cookie:
                            found_student_data_item = s_data_item
                            break
                    
                    if found_student_data_item:
                        counting_classes_list = []
                        try:
                            s_str = found_student_data_item.get('counts_classes_str', '[]')
                            if s_str.startswith('[') and s_str.endswith(']'):
                                s_content = s_str[1:-1]
                                if s_content.strip():
                                    counting_classes_list = [item.strip() for item in s_content.split(',')]
                        except Exception as e:
                            print(f"Error parsing counts_classes_str for student {found_student_data_item.get('class')}: '{found_student_data_item.get('counts_classes_str')}'. Error: {e}")
                        
                        response_payload.append({**found_student_data_item, "counting_classes": counting_classes_list})
                
                else:
                    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
                        self._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
                        return
                    
                    for student_data_item in students_data_store:
                        counting_classes_list = []
                        try:
                            s_str = student_data_item.get('counts_classes_str', '[]')
                            if s_str.startswith('[') and s_str.endswith(']'):
                                s_content = s_str[1:-1]
                                if s_content.strip():
                                    counting_classes_list = [item.strip() for item in s_content.split(',')]
                        except Exception as e:
                            print(f"Error parsing counts_classes_str for student {student_data_item.get('class')}: '{student_data_item.get('counts_classes_str')}'. Error: {e}")
                        response_payload.append({**student_data_item, "counting_classes": counting_classes_list})
            
            self._send_response(200, response_payload)
            return

        if path == '/api/student/counting-details':
            if not self.is_logged_in():
                self._send_response(401, {"error": "Authentication required"})
                return
            if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
                self._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
                return

            student_code_param = query.get('code', [None])[0]
            day_param_str = query.get('day', [None])[0]

            if not student_code_param or not day_param_str:
                self._send_response(400, {"error": "Missing 'code' or 'day' query parameter."})
                return
            if day_param_str not in ['1', '2', '3']:
                self._send_response(400, {"error": "Invalid 'day' parameter. Must be 1, 2, or 3."})
                return
            
            target_student_config = None
            with data_lock:
                for s_config in students_data_store:
                    if s_config.get('code') == student_code_param:
                        target_student_config = s_config
                        break

                if not target_student_config:
                    self._send_response(404, {"error": f"Student configuration with code '{student_code_param}' not found."})
                    return

                student_main_class_name = target_student_config.get('class')
                if not student_main_class_name:
                    self._send_response(500, {"error": f"Student with code '{student_code_param}' has no class assigned."})
                    return

                is_counted_by_field = f"iscountedby{day_param_str}"
                response_payload = []

                target_student_personal_counts_str = target_student_config.get('counts_classes_str', '[]')
                student_personal_counts_set = set()
                try:
                    if target_student_personal_counts_str.startswith('[') and target_student_personal_counts_str.endswith(']'):
                        content = target_student_personal_counts_str[1:-1]
                        if content.strip():
                            student_personal_counts_set = {c.strip() for c in content.split(',') if c.strip()}
                except Exception:
                    pass

                for class_being_evaluated in class_data_store:
                    if class_being_evaluated.get(is_counted_by_field) == student_main_class_name:
                        class_to_display_name = class_being_evaluated['class']
                        student_is_counting_this_class = class_to_display_name in student_personal_counts_set
                        also_counted_by_notes = []
                        for other_student_config in students_data_store:
                            if other_student_config.get('code') == student_code_param:
                                continue
                            other_student_counts_classes_str = other_student_config.get('counts_classes_str', '[]')
                            try:
                                if other_student_counts_classes_str.startswith('[') and other_student_counts_classes_str.endswith(']'):
                                    other_content = other_student_counts_classes_str[1:-1]
                                    if other_content.strip():
                                        if class_to_display_name in {c.strip() for c in other_content.split(',') if c.strip()}:
                                            also_counted_by_notes.append(other_student_config.get('note', 'Unknown Note'))
                            except Exception:
                                pass
                        
                        response_payload.append({
                            "class_name": class_to_display_name,
                            "is_counted_by_current_student": student_is_counting_this_class,
                            "also_counted_by_notes": sorted(list(set(also_counted_by_notes)))
                        })
                
                final_api_response = {
                    "student_note": target_student_config.get('note', ''),
                    "student_class": target_student_config.get('class', ''),
                    "counting_details": sorted(response_payload, key=lambda x: x['class_name'])
                }

            self._send_response(200, final_api_response)
            return

        if path == '/api/counts':
            if not self.is_logged_in():
                self._send_response(401, {"error": "Authentication required"})
                return

            is_student_session_for_counts = cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME) is not None
            if not (user_role in [ADMIN_ROLE, TEACHER_ROLE] or is_student_session_for_counts):
                self._send_response(403, {"error": "Forbidden: Access denied for your role."})
                return

            class_name = query.get('class', [None])[0]
            day_identifier = query.get('day', [None])[0]

            if not class_name or not day_identifier:
                self._send_response(400, {"error": "Missing 'class' or 'day' query parameter"})
                return
            
            student_auth_cookie_for_counts = cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
            if student_auth_cookie_for_counts:
                student_code = student_auth_cookie_for_counts.value
                if not is_student_allowed(student_code, class_name, day_identifier.lower()):
                    self._send_response(403, {"error": "Forbidden: You are not authorized to view counts for this class/day."})
                    return

            response_data = []
            try:
                day_specific_loaded_data = load_counts_from_db(day_identifier)

                if class_name in day_specific_loaded_data:
                    class_day_data = day_specific_loaded_data[class_name]
                    for type_val in ['student', 'teacher']:
                        for points_val in range(7):
                            count = class_day_data.get(type_val, {}).get(points_val, 0)
                            response_data.append({"type": type_val, "points": points_val, "count": count})
                    response_data.sort(key=lambda x: (x['type'], x['points']))
                else:
                    for type_val in ['student', 'teacher']:
                        for points_val in range(7):
                             response_data.append({"type": type_val, "points": points_val, "count": 0})
                self._send_response(200, response_data)
            except Exception as e:
                self._send_response(500, {"error": "Server error fetching counts."})
            return

        if path == '/login/google':
            try:
                if InstalledAppFlow is None:
                    self._send_response(500, {"error": "Google OAuth component (InstalledAppFlow) missing on server."})
                    return

                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRETS_FILE, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI
                )
                auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

                self.send_response(302)
                self.send_header('Location', auth_url)
                self.end_headers()
            except FileNotFoundError:
                self._send_response(500, {"error": "Google OAuth configuration error (server-side)."})
            except Exception as e:
                self._send_response(500, {"error": "Could not initiate Google login."})
            return

        if path == '/oauth2callback':
            try:
                code = query.get('code', [None])[0]
                if not code:
                    self._send_response(400, {"error": "Missing authorization code from Google."})
                    return

                if InstalledAppFlow is None or google_discovery_service is None:
                    self._send_response(500, {"error": "Google OAuth components missing on server."})
                    return

                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRETS_FILE, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI
                )
                flow.fetch_token(code=code)
                credentials = flow.credentials

                userinfo_service = google_discovery_service.build('oauth2', 'v2', credentials=credentials)
                user_info = userinfo_service.userinfo().get().execute()
                
                _user_email_from_google = user_info.get('email')
                user_email = _user_email_from_google.strip('"') if _user_email_from_google else None

                user_name_from_google_raw = user_info.get('name', _user_email_from_google)
                profile_picture = user_info.get('picture')

                name_for_cookie = ''
                if user_email:
                    name_for_cookie = user_email.split('@', 1)[0]
                elif user_name_from_google_raw:
                    name_for_cookie = user_name_from_google_raw.strip('"')

                if not user_email:
                    self._send_response(400, {"error": "Could not retrieve email from Google."})
                    return

                with data_lock:
                    if user_email not in user_password_store:
                        user_password_store[user_email] = {
                            'password_hash': '_GOOGLE_AUTH_USER_',
                            'profile_picture_url': profile_picture if profile_picture else '_NULL_',
                            'role': DEFAULT_ROLE_FOR_NEW_USERS
                        }
                        save_user_data_to_db()

                all_cookies = create_cookies(USERNAME_COOKIE_NAME, name_for_cookie, path='/', httponly=False) + \
                              create_cookies(SESSION_COOKIE_NAME, VALID_SESSION_VALUE, path='/') + \
                              create_cookie_clear_headers(CHANGE_PASSWORD_COOKIE_NAME, path='/') + \
                              create_cookies(GOOGLE_COOKIE_NAME, user_email, path='/', httponly=False)
                
                self.send_response(302)
                self.send_header('Location', '/menu.html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
                self.send_header('Access-Control-Allow-Credentials', 'true')

                for header_name, header_value in all_cookies:
                    self.send_header(header_name, header_value)
                
                self.end_headers()
            except Exception as e:
                self._send_response(500, {"error": "Google OAuth callback failed."})
            return

        if path == '/api/data/config':
            config_file_path = DATA_DIR / 'config.json'
            config_json = {}
            if config_file_path.is_file():
                try:
                    with open(config_file_path, 'r', encoding='utf-8') as f:
                        config_json = json.load(f)
                except Exception as e:
                    pass
            config_json['DOMAIN'] = DOMAIN
            config_json['PORT'] = PORT
            self._send_response(200, data=config_json)
            return

        if path == '/api/translations':
            if TRANSLATIONS_FILE_PATH.is_file():
                try:
                    with open(TRANSLATIONS_FILE_PATH, 'rb') as f:
                        content = f.read()
                    self._send_response(200, data=content, content_type='application/json')
                except Exception as e:
                    self._send_response(500, {"error": f"Error serving translations file: {e}"}, content_type='application/json')
            else:
                self._send_response(404, {"error": "Translations file not found."}, content_type='application/json')
            return

        if is_logged_in_flag and password_change_required and path not in allowed_get_paths_during_change and not path.startswith('/api/'):
            self.send_response(302)
            self.send_header('Location', '/change-password.html')
            self.end_headers()
            return

        if path == '/classes.html' or path == '/config.html':
            if self.is_logged_in(): 
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

                    # ...inside the login success block in do_POST...

                    # Generate a secure session token
                    session_token = generate_token(64)
                    # Optionally store the token in tokens.sql for tracking/auditing
                    store_token(username, session_token, self.client_address[0] if hasattr(self, 'client_address') else '_NULL_')
                    # Register the session token in the in-memory session store
                    self.__class__.active_sessions[session_token] = username
                    # Set the session cookie to the generated token
                    session_cookie_headers = create_cookies(SESSION_COOKIE_NAME, session_token, path='/')

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

        # --- STUDENT LOGIN Endpoint ---
        elif path == '/login/student':
            if not post_body_bytes:
                self._send_response(400, {"error": "Missing request body for student login"})
                return
            try:
                credentials = json.loads(post_body_bytes)
                student_code = credentials.get('code')
                print(f"DEBUG: Student login attempt with code: '{student_code}'")

                if not student_code:
                    self._send_response(400, {"error": "Missing student code"})
                    return

                found_student = None
                with data_lock: # Access students_data_store safely
                    for student_item in students_data_store:
                        if student_item.get('code') == student_code:
                            found_student = student_item
                            break
                
                if found_student:
                    student_note = found_student.get('note', 'Student') # Fallback note
                    student_actual_code = found_student.get('code') # This is the validated code

                    session_cookie_headers = create_cookies(SESSION_COOKIE_NAME, VALID_SESSION_VALUE, path='/')
                    user_cookie_headers = create_cookies(USERNAME_COOKIE_NAME, student_note, path='/', httponly=False) # httponly=False for JS access
                    student_auth_cookie_headers = create_cookies(SQL_AUTH_USER_STUDENT_COOKIE_NAME, student_actual_code, path='/', httponly=False) # httponly=False

                    all_cookie_headers = session_cookie_headers + user_cookie_headers + student_auth_cookie_headers

                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
                    self.send_header('Access-Control-Allow-Credentials', 'true')

                    for header_name, header_value in all_cookie_headers:
                        self.send_header(header_name, header_value)
                    
                    self.end_headers()
                    response_payload = {"success": True, "message": "Student login successful", "note": student_note, "class": found_student.get('class')}
                    self.wfile.write(json.dumps(response_payload).encode('utf-8'))
                    print(f"Student login successful for code: {student_actual_code} (Note: {student_note}). Cookies sent.")
                else:
                    self._send_response(401, {"error": "Invalid student code"})

            except json.JSONDecodeError:
                self._send_response(400, {"error": "Invalid JSON format in request body"})
            except Exception as e:
                print(f"Error during student login processing: {e}\n{traceback.format_exc()}")
                self._send_response(500, {"error": "Server error during student login"})
            return
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
            sql_student_auth_clear_headers = create_cookie_clear_headers(SQL_AUTH_USER_STUDENT_COOKIE_NAME, path='/') # Clear student auth cookie
            all_clear_headers = session_clear_headers + user_clear_headers + change_pw_clear_headers + sql_user_clear_headers + google_auth_clear_headers + sql_student_auth_clear_headers
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
                    if save_user_data_to_db():
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
            counts2 = data.get('counts2', 'F')  # Use 'counts2' to match SQL and JS
            counts3 = data.get('counts3', 'F')  # Use 'counts3' to match SQL and JS
            # Get new fields, defaulting to _NULL_
            iscountedby1 = data.get('iscountedby1', '_NULL_')
            iscountedby2 = data.get('iscountedby2', '_NULL_')
            iscountedby3 = data.get('iscountedby3', '_NULL_')

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
                        "counts1": counts1, "counts2": counts2, "counts3": counts3,
                        "iscountedby1": iscountedby1, "iscountedby2": iscountedby2,
                        "iscountedby3": iscountedby3
                    }
                    class_data_store.append(new_class)
                    # Sort the class_data_store alphabetically by class name
                    class_data_store.sort(key=lambda x: x['class'])
                    if save_class_data_to_db():
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
                    if save_class_data_to_db():
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
            count_field = data.get('countField') # e.g., "counts1", "counts2", "counts3"
            new_value = data.get('value')       # 'T' or 'F'

            if not all([class_name, count_field, new_value is not None]): # new_value can be 'F'
                self._send_response(400, {"error": "Missing class, countField, or value"})
                return
            
            # Ensure count_field matches the keys used in your data (including the typo)
            valid_count_fields = ["counts1", "counts2", "counts3"]
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
                    if save_class_data_to_db():
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

        # --- Handle /api/classes/update_iscountedby ---
        elif path == '/api/classes/update_iscountedby':
            # RBAC Check
            if current_user_role not in [ADMIN_ROLE, TEACHER_ROLE]: # Allow Admins and Teachers
                self._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
                return

            class_name_to_update = data.get('class')
            day_identifier = data.get('dayIdentifier') # '1', '2', or '3'
            new_value = data.get('value')

            if not all([class_name_to_update, day_identifier, new_value is not None]):
                self._send_response(400, {"error": "Missing class, dayIdentifier, or value"})
                return

            if day_identifier not in ['1', '2', '3']:
                self._send_response(400, {"error": "Invalid dayIdentifier. Must be '1', '2', or '3'."})
                return
            
            # Map dayIdentifier to the actual field name
            field_to_update = f"iscountedby{day_identifier}"

            # --- Server-side check for can_students_count_their_own_class ---
            # Read config.json directly for this check on every request
            allow_self_count_str = 'true' # Default to true (allow self-count)
            config_file_path = DATA_DIR / 'config.json'
            try:
                if config_file_path.is_file():
                    with open(config_file_path, 'r', encoding='utf-8') as f:
                        current_config_on_disk = json.load(f)
                    allow_self_count_str = current_config_on_disk.get('can_students_count_their_own_class', 'true')
                    print(f"DEBUG: Read 'can_students_count_their_own_class' from disk: {allow_self_count_str}")
                else:
                    print(f"Warning: {config_file_path} not found during iscountedby update. Defaulting 'can_students_count_their_own_class' to 'true'.")
            except json.JSONDecodeError:
                print(f"!!! ERROR: Invalid JSON in {config_file_path} during iscountedby update. Defaulting 'can_students_count_their_own_class' to 'true'.")
            except Exception as e:
                print(f"!!! ERROR reading {config_file_path} during iscountedby update: {e}. Defaulting 'can_students_count_their_own_class' to 'true'.")
            
            allow_self_count = allow_self_count_str.lower() == 'true'
            # --- End of direct config file read ---

            # Old way using in-memory server_config:
            # allow_self_count_str = server_config.get('can_students_count_their_own_class', 'true') # Default to true if missing
            # allow_self_count = allow_self_count_str.lower() == 'true'

            if not allow_self_count and new_value == class_name_to_update:
                self._send_response(400, {"error": f"Configuration prevents class '{class_name_to_update}' from counting itself."})
                return
            # --- End server-side check ---

            success = False
            message = "Failed to update class counting assignment."
            status_code = 500

            with data_lock:
                class_found = False
                for cls_item in class_data_store:
                    if cls_item['class'] == class_name_to_update:
                        cls_item[field_to_update] = new_value
                        class_found = True
                        break
                
                if not class_found:
                    message = f"Class '{class_name_to_update}' not found."
                    status_code = 404
                else:
                    if save_class_data_to_db():
                        success = True
                        message = f"Assignment for class '{class_name_to_update}' on day {day_identifier} updated to '{new_value}' and saved."
                        status_code = 200
                    else:
                        message = f"Assignment for class '{class_name_to_update}' updated in memory, but FAILED to save to file."
                        status_code = 500
            if success:
                self._send_response(status_code, {"success": True, "message": message})
            else:
                self._send_response(status_code, {"error": message})
            return

        # --- Handle /api/students/remove ---
        elif path == '/api/students/remove':
            if not self.is_logged_in(): # Should be caught by earlier checks
                self._send_response(401, {"error": "Authentication required"})
                return
            # RBAC Check
            if current_user_role not in [ADMIN_ROLE, TEACHER_ROLE]: # Allow Admins and Teachers
                self._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
                return

            student_code_to_remove = data.get('code') # Identify student by their 'code'
            if not student_code_to_remove:
                self._send_response(400, {"error": "Missing 'code' of student configuration to remove"})
                return

            success = False
            message = "Failed to remove student configuration."
            status_code = 500

            with data_lock:
                original_len = len(students_data_store)
                # Filter out the student to remove
                students_data_store[:] = [s_config for s_config in students_data_store if s_config.get('code') != student_code_to_remove]
                
                if len(students_data_store) < original_len: # If something was removed
                    if save_students_data_to_db():
                        success = True
                        # We don't easily have the note/class here without finding it first, so a generic message is fine
                        message = f"Student configuration with code '{student_code_to_remove}' removed successfully."
                        status_code = 200
                    else:
                        message = f"Student configuration with code '{student_code_to_remove}' removed from memory, but FAILED to save to file."
                        status_code = 500 # Internal Server Error
                else:
                    message = f"Student configuration with code '{student_code_to_remove}' not found."
                    status_code = 404 # Not Found
            self._send_response(status_code, {"success": success, "message": message} if success else {"error": message})
            return

        # --- Handle /api/students/add ---
        elif path == '/api/students/add':
            if not self.is_logged_in():
                self._send_response(401, {"error": "Authentication required"})
                return
            # RBAC Check - Allow Admins and Teachers to add student configurations
            if current_user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
                self._send_response(403, {"error": "Forbidden: Administrator access required."})
                return

            student_class = data.get('class')
            note = data.get('note', '') # Default to empty string if note is not provided

            if not student_class:
                self._send_response(400, {"error": "Missing 'class' for the new student configuration."})
                return

            success = False
            message = "Failed to add student configuration."
            status_code = 500

            with data_lock:
                # Removed the check for existing student configuration by class.
                # Now multiple configurations can exist for the same class,
                # distinguished by their notes or codes.
                new_student_config = {
                    "code": generate_random_code(), # Server generates the code
                    "class": student_class,
                    "note": note,
                    "counts_classes_str": "[]" # New students start with no classes to count
                }
                students_data_store.append(new_student_config)
                students_data_store.sort(key=lambda x: (x['class'], x.get('note', ''))) # Keep sorted by class, then note

                if save_students_data_to_db():
                    success = True
                    message = f"Student configuration for class '{student_class}' (Note: '{note}') added successfully."
                    status_code = 201 # Created
                else:
                    students_data_store.pop() # Revert in-memory change if save fails
                    message = f"Failed to save new student configuration for '{student_class}' (Note: '{note}') to file."
                    status_code = 500
            self._send_response(status_code, {"success": success, "message": message} if success else {"error": message})
            return
        
        # --- Handle /api/student/update-counting-class ---
        elif path == '/api/student/update-counting-class': # POST endpoint
            if not self.is_logged_in():
                self._send_response(401, {"error": "Authentication required"})
                return
            # RBAC Check - Only Admins/Teachers can modify student counting assignments
            if current_user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
                self._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
                return

            student_code_to_update = data.get('student_code') # Changed from student_note
            class_to_update = data.get('class_name')
            is_counting = data.get('is_counting') # boolean

            if not student_code_to_update or not class_to_update or is_counting is None:
                self._send_response(400, {"error": "Missing student_code, class_name, or is_counting status."})
                return

            success = False
            message = "Failed to update student's counting classes."
            status_code = 500
            student_note_for_message = "Unknown" # For user-friendly messages

            with data_lock:
                target_student_config = next((s for s in students_data_store if s.get('code') == student_code_to_update), None)

                if not target_student_config:
                    message = f"Student configuration with code '{student_code_to_update}' not found."
                    status_code = 404
                else:
                    student_note_for_message = target_student_config.get('note', student_code_to_update)
                    counts_str = target_student_config.get('counts_classes_str', '[]')
                    current_counts_set = set()
                    if counts_str.startswith('[') and counts_str.endswith(']'):
                        content = counts_str[1:-1]
                        if content.strip():
                            current_counts_set = {c.strip() for c in content.split(',') if c.strip()}
                    
                    if is_counting:
                        current_counts_set.add(class_to_update)
                    else:
                        current_counts_set.discard(class_to_update) # Use discard to not raise error if not present
                    
                    # Reconstruct the string, sorted for consistency
                    sorted_list_of_classes = sorted(list(current_counts_set))
                    new_counts_classes_str = f"[{', '.join(sorted_list_of_classes)}]" if sorted_list_of_classes else "[]"
                    
                    target_student_config['counts_classes_str'] = new_counts_classes_str

                    if save_students_data_to_db():
                        success = True
                        action = "added to" if is_counting else "removed from"
                        message = f"Class '{class_to_update}' {action} student '{student_note_for_message}'s counting list."
                        status_code = 200
                    else:
                        # Attempt to revert in-memory change if save fails (though original counts_str was overwritten)
                        # For simplicity, we'll just report the error. A more robust undo would store original_counts_str.
                        message = f"Failed to save updated counting list for student '{student_note_for_message}' to file."
                        status_code = 500
            self._send_response(status_code, {"success": success, "message": message} if success else {"error": message})
            return
        # --- Handle /api/auth/change ---
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
                    if save_user_data_to_db():
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
                    if save_user_data_to_db():
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
        elif path == '/api/language/set':
            # This endpoint can be accessed whether logged in or not.
            if not post_body_bytes:
                self._send_response(400, {"error": "Missing request body"})
                return
            try:
                data = json.loads(post_body_bytes)
                language_code = data.get('language')

                if language_code not in ['cs', 'en']:
                    self._send_response(400, {"error": "Invalid language code. Must be 'cs' or 'en'."})
                    return

                # Set cookie to expire in 1 year
                max_age_1_year = 365 * 24 * 60 * 60
                language_cookie_headers = create_cookies(
                    LANGUAGE_COOKIE_NAME,
                    language_code,
                    path='/',
                    max_age=max_age_1_year,
                    httponly=False # Allow JS to read for UI updates if needed
                )

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
                self.send_header('Access-Control-Allow-Credentials', 'true')

                for header_name, header_value in language_cookie_headers:
                    self.send_header(header_name, header_value)
                
                self.end_headers()
                response_payload = {"success": True, "message": f"Language set to {language_code}"}
                self.wfile.write(json.dumps(response_payload).encode('utf-8'))
                print(f"Language cookie set to '{language_code}'.")
            except json.JSONDecodeError:
                self._send_response(400, {"error": "Invalid JSON payload"})
            except Exception as e:
                print(f"Error in /api/language/set: {e}")
                traceback.print_exc()
                self._send_response(500, {"error": "Server error while setting language."})
            return # Handled
        else:
            print(f"Authenticated POST request to unknown path: {path}")
            self._send_response(404, {"error": "API endpoint not found"})

# --- End of ColorDaysHandler modifications ---
