"""GET endpoint handlers for ColorDays API."""

import json
import urllib.parse
from pathlib import Path

from config import (
    ADMIN_ROLE,
    TEACHER_ROLE,
    SQL_AUTH_USER_STUDENT_COOKIE_NAME,
    CHANGE_PASSWORD_COOKIE_NAME,
    DATA_DIR,
    TRANSLATIONS_FILE_PATH,
    DOMAIN,
    PORT,
    CLIENT_SECRETS_FILE,
    GOOGLE_SCOPES,
    GOOGLE_REDIRECT_URI,
    USERNAME_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    GOOGLE_COOKIE_NAME,
    VALID_SESSION_VALUE,
    DEFAULT_ROLE_FOR_NEW_USERS,
)
from auth import get_current_user_info
from data_manager import (
    load_counts_from_db,
    is_student_allowed,
    user_password_store,
    class_data_store,
    students_data_store,
    data_lock,
    save_user_data_to_db,
)
from utils import create_cookies, create_cookie_clear_headers

# These will be set by server.py if available
InstalledAppFlow = None
google_discovery_service = None


def handle_api_users(handler):
    """GET /api/users - List all users."""
    if not handler.is_logged_in():
        handler._send_response(401, {"error": "Authentication required"})
        return

    handler.handle_get_users()


def handle_api_classes(handler):
    """GET /api/classes - List all classes."""
    user_key, user_role = get_current_user_info(handler)
    cookies = handler.get_cookies()

    if not handler.is_logged_in():
        handler._send_response(401, {"error": "Authentication required"})
        return

    is_student_session = cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME) is not None

    if not (user_role in [ADMIN_ROLE, TEACHER_ROLE] or is_student_session):
        handler._send_response(403, {"error": "Forbidden: Access to this resource is restricted for your account type."})
        return

    with data_lock:
        response_data = list(class_data_store)
    handler._send_response(200, response_data)


def handle_api_students(handler):
    """GET /api/students - List all students."""
    user_key, user_role = get_current_user_info(handler)
    cookies = handler.get_cookies()

    if not handler.is_logged_in():
        handler._send_response(401, {"error": "Authentication required"})
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
                    print(f"Error parsing counts_classes_str: {e}")

                response_payload.append({**found_student_data_item, "counting_classes": counting_classes_list})

        else:
            if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
                handler._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
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
                    print(f"Error parsing counts_classes_str: {e}")
                response_payload.append({**student_data_item, "counting_classes": counting_classes_list})

    handler._send_response(200, response_payload)


def handle_api_student_counting_details(handler):
    """GET /api/student/counting-details - Get student counting details."""
    user_key, user_role = get_current_user_info(handler)
    parsed_path = urllib.parse.urlparse(handler.path)
    query = urllib.parse.parse_qs(parsed_path.query)

    if not handler.is_logged_in():
        handler._send_response(401, {"error": "Authentication required"})
        return
    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        handler._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
        return

    student_code_param = query.get('code', [None])[0]
    day_param_str = query.get('day', [None])[0]

    if not student_code_param or not day_param_str:
        handler._send_response(400, {"error": "Missing 'code' or 'day' query parameter."})
        return
    if day_param_str not in ['1', '2', '3']:
        handler._send_response(400, {"error": "Invalid 'day' parameter. Must be 1, 2, or 3."})
        return

    target_student_config = None
    with data_lock:
        for s_config in students_data_store:
            if s_config.get('code') == student_code_param:
                target_student_config = s_config
                break

        if not target_student_config:
            handler._send_response(404, {"error": f"Student configuration with code '{student_code_param}' not found."})
            return

        student_main_class_name = target_student_config.get('class')
        if not student_main_class_name:
            handler._send_response(500, {"error": f"Student with code '{student_code_param}' has no class assigned."})
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

    handler._send_response(200, final_api_response)


def handle_api_counts(handler):
    """GET /api/counts - Get count data for a class/day."""
    user_key, user_role = get_current_user_info(handler)
    cookies = handler.get_cookies()
    parsed_path = urllib.parse.urlparse(handler.path)
    query = urllib.parse.parse_qs(parsed_path.query)

    if not handler.is_logged_in():
        handler._send_response(401, {"error": "Authentication required"})
        return

    is_student_session_for_counts = cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME) is not None
    if not (user_role in [ADMIN_ROLE, TEACHER_ROLE] or is_student_session_for_counts):
        handler._send_response(403, {"error": "Forbidden: Access denied for your role."})
        return

    class_name = query.get('class', [None])[0]
    day_identifier = query.get('day', [None])[0]

    if not class_name or not day_identifier:
        handler._send_response(400, {"error": "Missing 'class' or 'day' query parameter"})
        return

    student_auth_cookie_for_counts = cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
    if student_auth_cookie_for_counts:
        student_code = student_auth_cookie_for_counts.value
        if not is_student_allowed(student_code, class_name, day_identifier.lower()):
            handler._send_response(403, {"error": "Forbidden: You are not authorized to view counts for this class/day."})
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
        handler._send_response(200, response_data)
    except Exception as e:
        handler._send_response(500, {"error": "Server error fetching counts."})


def handle_api_data_config(handler):
    """GET /api/data/config - Get server configuration."""
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
    handler._send_response(200, data=config_json)


def handle_api_translations(handler):
    """GET /api/translations - Get language translations."""
    if TRANSLATIONS_FILE_PATH.is_file():
        try:
            with open(TRANSLATIONS_FILE_PATH, 'rb') as f:
                content = f.read()
            handler._send_response(200, data=content, content_type='application/json')
        except Exception as e:
            handler._send_response(500, {"error": f"Error serving translations file: {e}"}, content_type='application/json')
    else:
        handler._send_response(404, {"error": "Translations file not found."}, content_type='application/json')


def handle_login_google(handler):
    """GET /login/google - Initiate Google OAuth flow."""
    try:
        if InstalledAppFlow is None:
            handler._send_response(500, {"error": "Google OAuth component (InstalledAppFlow) missing on server."})
            return

        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI
        )
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

        handler.send_response(302)
        handler.send_header('Location', auth_url)
        handler.end_headers()
    except FileNotFoundError:
        handler._send_response(500, {"error": "Google OAuth configuration error (server-side)."})
    except Exception as e:
        handler._send_response(500, {"error": "Could not initiate Google login."})


def handle_oauth2callback(handler):
    """GET /oauth2callback - Handle Google OAuth callback."""
    parsed_path = urllib.parse.urlparse(handler.path)
    query = urllib.parse.parse_qs(parsed_path.query)

    try:
        code = query.get('code', [None])[0]
        if not code:
            handler._send_response(400, {"error": "Missing authorization code from Google."})
            return

        if InstalledAppFlow is None or google_discovery_service is None:
            handler._send_response(500, {"error": "Google OAuth components missing on server."})
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
            handler._send_response(400, {"error": "Could not retrieve email from Google."})
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

        handler.send_response(302)
        handler.send_header('Location', '/menu.html')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
        handler.send_header('Access-Control-Allow-Credentials', 'true')

        for header_name, header_value in all_cookies:
            handler.send_header(header_name, header_value)

        handler.end_headers()
    except Exception as e:
        handler._send_response(500, {"error": "Google OAuth callback failed."})


# Route mapping
GET_ROUTES = {
    '/api/users': handle_api_users,
    '/api/classes': handle_api_classes,
    '/api/students': handle_api_students,
    '/api/student/counting-details': handle_api_student_counting_details,
    '/api/counts': handle_api_counts,
    '/api/data/config': handle_api_data_config,
    '/api/translations': handle_api_translations,
    '/login/google': handle_login_google,
    '/oauth2callback': handle_oauth2callback,
}
