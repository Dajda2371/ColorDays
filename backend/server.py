import http.server
import socketserver
import json
import urllib.parse
from http.cookies import SimpleCookie
import os

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
from auth import get_current_user_info, is_user_using_oauth
from data_manager import (
    load_counts_from_file,
    save_counts_to_file,
    load_class_data_from_sql,
    save_class_data_to_sql,
    load_students_data_from_sql,
    save_students_data_to_sql,
    load_user_data_from_sql,
    save_user_data_to_sql,
    load_main_config_from_json,
    save_main_config_to_json,
    get_sql_file_path_for_day,
    is_student_allowed,
    user_password_store,
    class_data_store,
    students_data_store,
    data_lock,
)

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

            success = save_user_data_to_sql()

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
                if save_user_data_to_sql():
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
                if save_user_data_to_sql():
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
            
            try:
                target_file_path = get_sql_file_path_for_day(day_identifier)
            except ValueError as e:
                self._send_response(400, {"error": str(e)})
                return

            student_auth_cookie_for_counts = cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
            if student_auth_cookie_for_counts:
                student_code = student_auth_cookie_for_counts.value
                if not is_student_allowed(student_code, class_name, day_identifier.lower()):
                    self._send_response(403, {"error": "Forbidden: You are not authorized to view counts for this class/day."})
                    return

            response_data = []
            try:
                day_specific_loaded_data = load_counts_from_file(target_file_path)

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
                        save_user_data_to_sql()

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
