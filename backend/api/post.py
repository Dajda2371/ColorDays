"""POST endpoint handlers for ColorDays API."""

import json
import traceback
import collections
from pathlib import Path

from config import (
    ADMIN_ROLE,
    TEACHER_ROLE,
    SQL_AUTH_USER_STUDENT_COOKIE_NAME,
    CHANGE_PASSWORD_COOKIE_NAME,
    DATA_DIR,
    USERNAME_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    SQL_COOKIE_NAME,
    GOOGLE_COOKIE_NAME,
    LANGUAGE_COOKIE_NAME,
    VALID_SESSION_VALUE,
    DEFAULT_ROLE_FOR_NEW_USERS,
)
from auth import get_current_user_info, is_user_using_oauth
from data_manager import (
    save_counts_to_db,
    load_counts_from_db,
    save_class_data_to_db,
    save_students_data_to_db,
    save_user_data_to_db,
    load_main_config_from_json,
    save_main_config_to_json,
    is_student_allowed,
    user_password_store,
    class_data_store,
    students_data_store,
    data_lock,
)
from utils import (
    generate_random_code,
    hash_password,
    verify_password,
    create_cookies,
    create_cookie_clear_headers,
    generate_token,
    store_token,
)


# =============================================================================
# Authentication Endpoints
# =============================================================================

def handle_login(handler):
    """POST /login - Username/password login."""
    content_length = int(handler.headers.get('Content-Length', 0))
    if content_length == 0:
        handler._send_response(400, {"error": "Missing request body for login"})
        return

    try:
        post_body_bytes = handler.rfile.read(content_length)
        credentials = json.loads(post_body_bytes)
        username = credentials.get('username')
        submitted_password = credentials.get('password')
        print(f"DEBUG: Login attempt for username: '{username}'")

        # Initialize login result and extra headers
        login_successful = False
        extra_cookie_headers = []

        stored_info = user_password_store.get(username)

        if stored_info and submitted_password:
            login_successful, extra_cookie_headers = verify_password(stored_info, submitted_password, username)
            if not login_successful:
                print(f"Password verification failed for user: {username}")
        elif not stored_info:
            print(f"Login attempt failed: Username '{username}' not found.")
        elif not submitted_password:
            print(f"Login attempt failed: No password provided for user '{username}'.")

        if login_successful:
            # Prepare the standard cookies
            cleaned_username = username.strip('"') if username else ""
            user_cookie_headers = create_cookies(USERNAME_COOKIE_NAME, cleaned_username, path='/', httponly=False)

            # Generate a secure session token
            session_token = generate_token(64)
            store_token(username, session_token, handler.client_address[0] if hasattr(handler, 'client_address') else '_NULL_')
            handler.__class__.active_sessions[session_token] = username
            session_cookie_headers = create_cookies(SESSION_COOKIE_NAME, session_token, path='/')

            sql_user_cookie_headers = create_cookies(SQL_COOKIE_NAME, username, path='/', httponly=False)

            all_cookie_headers = user_cookie_headers + session_cookie_headers + extra_cookie_headers + sql_user_cookie_headers

            # Send response headers manually
            handler.send_response(200)
            handler.send_header('Content-type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
            handler.send_header('Access-Control-Allow-Credentials', 'true')

            print(f"DEBUG: Preparing to send {len(all_cookie_headers)} cookie(s)...")
            for header_name, header_value in all_cookie_headers:
                handler.send_header(header_name, header_value)
                print(f"DEBUG: Sent {header_name} header: {header_value}")

            handler.end_headers()

            # Include role in login response
            role = user_password_store.get(username, {}).get('role', DEFAULT_ROLE_FOR_NEW_USERS)

            response_payload = {
                "success": True,
                "message": "Login successful",
                "username": cleaned_username,
                "role": role
            }
            response_body = json.dumps(response_payload).encode('utf-8')
            handler.wfile.write(response_body)

            print(f"Login successful for user: {username}, {len(all_cookie_headers)} session/other cookie(s) sent.")

        else:
            handler._send_response(401, {"error": "Invalid username or password"})

    except json.JSONDecodeError:
        print("Error: Invalid JSON received for login.")
        handler._send_response(400, {"error": "Invalid JSON format in request body"})
    except Exception as e:
        print(f"Error during login processing: {e}")
        print(traceback.format_exc())
        handler._send_response(500, {"error": "Server error during login"})


def handle_login_student(handler):
    """POST /login/student - Student code login."""
    content_length = int(handler.headers.get('Content-Length', 0))
    if content_length == 0:
        handler._send_response(400, {"error": "Missing request body for student login"})
        return

    try:
        post_body_bytes = handler.rfile.read(content_length)
        credentials = json.loads(post_body_bytes)
        student_code = credentials.get('code')
        print(f"DEBUG: Student login attempt with code: '{student_code}'")

        if not student_code:
            handler._send_response(400, {"error": "Missing student code"})
            return

        found_student = None
        with data_lock:
            for student_item in students_data_store:
                if student_item.get('code') == student_code:
                    found_student = student_item
                    break

        if found_student:
            student_note = found_student.get('note', 'Student')
            student_actual_code = found_student.get('code')

            session_cookie_headers = create_cookies(SESSION_COOKIE_NAME, VALID_SESSION_VALUE, path='/')
            user_cookie_headers = create_cookies(USERNAME_COOKIE_NAME, student_note, path='/', httponly=False)
            student_auth_cookie_headers = create_cookies(SQL_AUTH_USER_STUDENT_COOKIE_NAME, student_actual_code, path='/', httponly=False)

            all_cookie_headers = session_cookie_headers + user_cookie_headers + student_auth_cookie_headers

            handler.send_response(200)
            handler.send_header('Content-type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
            handler.send_header('Access-Control-Allow-Credentials', 'true')

            for header_name, header_value in all_cookie_headers:
                handler.send_header(header_name, header_value)

            handler.end_headers()
            response_payload = {"success": True, "message": "Student login successful", "note": student_note, "class": found_student.get('class')}
            handler.wfile.write(json.dumps(response_payload).encode('utf-8'))
            print(f"Student login successful for code: {student_actual_code} (Note: {student_note}). Cookies sent.")
        else:
            handler._send_response(401, {"error": "Invalid student code"})

    except json.JSONDecodeError:
        handler._send_response(400, {"error": "Invalid JSON format in request body"})
    except Exception as e:
        print(f"Error during student login processing: {e}\n{traceback.format_exc()}")
        handler._send_response(500, {"error": "Server error during student login"})


def handle_logout(handler):
    """POST /logout - Logout and clear session."""
    print("Logout request received. Preparing cookie clearing headers.")

    session_clear_headers = create_cookie_clear_headers(SESSION_COOKIE_NAME, path='/')
    user_clear_headers = create_cookie_clear_headers(USERNAME_COOKIE_NAME, path='/')
    change_pw_clear_headers = create_cookie_clear_headers(CHANGE_PASSWORD_COOKIE_NAME, path='/')
    sql_user_clear_headers = create_cookie_clear_headers(SQL_COOKIE_NAME, path='/')
    google_auth_clear_headers = create_cookie_clear_headers(GOOGLE_COOKIE_NAME, path='/')
    sql_student_auth_clear_headers = create_cookie_clear_headers(SQL_AUTH_USER_STUDENT_COOKIE_NAME, path='/')
    all_clear_headers = session_clear_headers + user_clear_headers + change_pw_clear_headers + sql_user_clear_headers + google_auth_clear_headers + sql_student_auth_clear_headers

    handler.send_response(200)
    handler.send_header('Content-type', 'application/json')
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
    handler.send_header('Access-Control-Allow-Credentials', 'true')

    print(f"DEBUG: Preparing to send {len(all_clear_headers)} cookie clearing header(s)...")
    for header_name, header_value in all_clear_headers:
        handler.send_header(header_name, header_value)
        print(f"DEBUG: Sent Set-Cookie expiration header: {header_value}")

    handler.end_headers()

    response_body = json.dumps({"success": True, "message": "Logged out successfully"}).encode('utf-8')
    handler.wfile.write(response_body)

    print("Logout successful, cookie expiration headers sent.")


def handle_auth_change(handler, data):
    """POST /api/auth/change - Change password for current user."""
    user_key_for_rbac, _ = get_current_user_info(handler)

    if not user_key_for_rbac:
        print("Error: Username cookie missing in authenticated /api/auth/change request.")
        handler._send_response(401, {"error": "Authentication error: User identity not found."})
        return

    if is_user_using_oauth(user_key_for_rbac, handler):
        handler._send_response(403, {"error": "Password change not allowed for Google OAuth users."})
        return

    username_for_messages = user_key_for_rbac

    old_password = data.get('oldPassword')
    new_password = data.get('newPassword')

    # Check for the cookie and force verification if present
    cookies = handler.get_cookies()
    verification_needed = True
    if cookies.get(CHANGE_PASSWORD_COOKIE_NAME):
        print(f"DEBUG: Cookie '{CHANGE_PASSWORD_COOKIE_NAME}' found. Forcing verification_needed to False.")
        verification_needed = False

    if not user_key_for_rbac or not new_password:
        handler._send_response(400, {"error": "Missing username or new password"})
        return

    success = False
    message = "Failed to change password."
    status_code = 500
    save_needed = False

    with data_lock:
        stored_user_data = user_password_store.get(user_key_for_rbac)

        if not stored_user_data:
            message = f"User '{username_for_messages}' not found."
            status_code = 404
        else:
            if verification_needed:
                is_old_valid, _ = verify_password(stored_user_data, old_password, username_for_messages)
                if not is_old_valid:
                    message = "Old password verification failed."
                    status_code = 401
                    handler._send_response(status_code, {"error": message})
                    return

            try:
                hashed_pw = hash_password(new_password)
                user_password_store[user_key_for_rbac]['password_hash'] = hashed_pw
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
                status_code = 200
            else:
                success = False
                message = f"Password changed in memory for '{username_for_messages}', but FAILED to save to file."
                status_code = 500

    if success:
        extra_headers_on_success = []
        cookies = handler.get_cookies()
        if cookies.get(CHANGE_PASSWORD_COOKIE_NAME):
            print(f"DEBUG: Password change successful, clearing '{CHANGE_PASSWORD_COOKIE_NAME}' cookie.")
            clear_headers = create_cookie_clear_headers(CHANGE_PASSWORD_COOKIE_NAME, path='/')
            extra_headers_on_success.extend(clear_headers)

        handler.send_response(status_code)
        handler.send_header('Content-type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
        handler.send_header('Access-Control-Allow-Credentials', 'true')

        for header_name, header_value in extra_headers_on_success:
            handler.send_header(header_name, header_value)
            print(f"DEBUG: Sent extra header: {header_name}: {header_value}")

        handler.end_headers()
        response_body = json.dumps({"success": True, "message": message}).encode('utf-8')
        handler.wfile.write(response_body)
    else:
        handler._send_response(status_code, {"error": message})


# =============================================================================
# User Management Endpoints
# =============================================================================

def handle_api_users_post(handler, data):
    """POST /api/users - Add user."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role != ADMIN_ROLE:
        handler._send_response(403, {"error": "Forbidden: Administrator access required."})
        return

    username = data.get("username", "").strip()

    if not username:
        handler._send_response(400, {"error": "Username required"})
        return

    if username in user_password_store:
        handler._send_response(400, {"error": "User already exists"})
        return

    user_password_store[username] = {
        'password_hash': 'NOT_SET',
        'profile_picture_url': '_NULL_',
        'role': DEFAULT_ROLE_FOR_NEW_USERS
    }

    success = save_user_data_to_db()

    if success:
        handler._send_response(200, {"message": "User added"})
    else:
        handler._send_response(500, {"error": "Failed to save user data"})


def handle_api_users_remove(handler, data):
    """POST /api/users/remove - Remove user."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role != ADMIN_ROLE:
        handler._send_response(403, {"error": "Forbidden: Administrator access required."})
        return

    username = data.get("username")

    if not username:
        handler._send_response(400, {"error": "Missing username"})
        return

    if username == 'admin':
        handler._send_response(403, {"error": "Cannot remove the admin user."})
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
        handler._send_response(status_code, {"success": True, "message": message})
    else:
        handler._send_response(status_code, {"error": message})


def handle_api_users_set(handler, data):
    """POST /api/users/set - Set user password."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role != ADMIN_ROLE:
        handler._send_response(403, {"error": "Forbidden: Administrator access required."})
        return

    username = data.get("username")
    new_password = data.get("new_password")

    if is_user_using_oauth(username):
        handler._send_response(403, {"error": "Password change not allowed for Google OAuth users."})
        return

    if not username or not new_password:
        handler._send_response(400, {"error": "Missing username or new_password"})
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
        handler._send_response(status_code, {"success": True, "message": message})
    else:
        handler._send_response(status_code, {"error": message})


# =============================================================================
# Class Management Endpoints
# =============================================================================

def handle_api_classes_add(handler, data):
    """POST /api/classes/add - Add class."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role != ADMIN_ROLE:
        handler._send_response(403, {"error": "Forbidden: Administrator access required."})
        return

    class_name = data.get('class')
    teacher = data.get('teacher')
    counts1 = data.get('counts1', 'F')
    counts2 = data.get('counts2', 'F')
    counts3 = data.get('counts3', 'F')
    iscountedby1 = data.get('iscountedby1', '_NULL_')
    iscountedby2 = data.get('iscountedby2', '_NULL_')
    iscountedby3 = data.get('iscountedby3', '_NULL_')

    if not class_name or not teacher:
        handler._send_response(400, {"error": "Missing class name or teacher"})
        return

    if counts1 not in ['T', 'F'] or counts2 not in ['T', 'F'] or counts3 not in ['T', 'F']:
        handler._send_response(400, {"error": "Invalid counts values (must be T or F)"})
        return

    success = False
    message = "Failed to add class."
    status_code = 500

    with data_lock:
        if any(c['class'] == class_name for c in class_data_store):
            message = f"Class '{class_name}' already exists."
            status_code = 409
        else:
            new_class = {
                "class": class_name, "teacher": teacher,
                "counts1": counts1, "counts2": counts2, "counts3": counts3,
                "iscountedby1": iscountedby1, "iscountedby2": iscountedby2,
                "iscountedby3": iscountedby3
            }
            class_data_store.append(new_class)
            class_data_store.sort(key=lambda x: x['class'])
            if save_class_data_to_db():
                success = True
                message = f"Class '{class_name}' added successfully."
                status_code = 201
            else:
                class_data_store.pop()
                message = f"Failed to save class '{class_name}' to file."
                status_code = 500

    if success:
        handler._send_response(status_code, {"success": True, "message": message})
    else:
        handler._send_response(status_code, {"error": message})


def handle_api_classes_remove(handler, data):
    """POST /api/classes/remove - Remove class."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role != ADMIN_ROLE:
        handler._send_response(403, {"error": "Forbidden: Administrator access required."})
        return

    class_name_to_remove = data.get('class')
    if not class_name_to_remove:
        handler._send_response(400, {"error": "Missing class name to remove"})
        return

    success = False
    message = "Failed to remove class."
    status_code = 500

    with data_lock:
        original_len = len(class_data_store)
        class_data_store[:] = [c for c in class_data_store if c['class'] != class_name_to_remove]
        if len(class_data_store) < original_len:
            if save_class_data_to_db():
                success = True
                message = f"Class '{class_name_to_remove}' removed successfully."
                status_code = 200
            else:
                message = f"Class '{class_name_to_remove}' removed from memory, but FAILED to save to file."
                status_code = 500
        else:
            message = f"Class '{class_name_to_remove}' not found."
            status_code = 404

    if success:
        handler._send_response(status_code, {"success": True, "message": message})
    else:
        handler._send_response(status_code, {"error": message})


def handle_api_classes_update_counts(handler, data):
    """POST /api/classes/update_counts - Update counting days."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role != ADMIN_ROLE:
        handler._send_response(403, {"error": "Forbidden: Administrator access required."})
        return

    class_name = data.get('class')
    count_field = data.get('countField')
    new_value = data.get('value')

    if not all([class_name, count_field, new_value is not None]):
        handler._send_response(400, {"error": "Missing class, countField, or value"})
        return

    valid_count_fields = ["counts1", "counts2", "counts3"]
    if count_field not in valid_count_fields:
        handler._send_response(400, {"error": f"Invalid countField. Must be one of {valid_count_fields}"})
        return

    if new_value not in ['T', 'F']:
        handler._send_response(400, {"error": "Invalid value. Must be 'T' or 'F'"})
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
                status_code = 500

    if success:
        handler._send_response(status_code, {"success": True, "message": message})
    else:
        handler._send_response(status_code, {"error": message})


def handle_api_classes_update_iscountedby(handler, data):
    """POST /api/classes/update_iscountedby - Update counting assignments."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        handler._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
        return

    class_name_to_update = data.get('class')
    day_identifier = data.get('dayIdentifier')
    new_value = data.get('value')

    if not all([class_name_to_update, day_identifier, new_value is not None]):
        handler._send_response(400, {"error": "Missing class, dayIdentifier, or value"})
        return

    if day_identifier not in ['1', '2', '3']:
        handler._send_response(400, {"error": "Invalid dayIdentifier. Must be '1', '2', or '3'."})
        return

    field_to_update = f"iscountedby{day_identifier}"

    # Server-side check for can_students_count_their_own_class
    allow_self_count_str = 'true'
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

    if not allow_self_count and new_value == class_name_to_update:
        handler._send_response(400, {"error": f"Configuration prevents class '{class_name_to_update}' from counting itself."})
        return

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
        handler._send_response(status_code, {"success": True, "message": message})
    else:
        handler._send_response(status_code, {"error": message})


# =============================================================================
# Student Management Endpoints
# =============================================================================

def handle_api_students_add(handler, data):
    """POST /api/students/add - Add student."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        handler._send_response(403, {"error": "Forbidden: Administrator access required."})
        return

    student_class = data.get('class')
    note = data.get('note', '')

    if not student_class:
        handler._send_response(400, {"error": "Missing 'class' for the new student configuration."})
        return

    success = False
    message = "Failed to add student configuration."
    status_code = 500

    with data_lock:
        new_student_config = {
            "code": generate_random_code(),
            "class": student_class,
            "note": note,
            "counts_classes_str": "[]"
        }
        students_data_store.append(new_student_config)
        students_data_store.sort(key=lambda x: (x['class'], x.get('note', '')))

        if save_students_data_to_db():
            success = True
            message = f"Student configuration for class '{student_class}' (Note: '{note}') added successfully."
            status_code = 201
        else:
            students_data_store.pop()
            message = f"Failed to save new student configuration for '{student_class}' (Note: '{note}') to file."
            status_code = 500

    handler._send_response(status_code, {"success": success, "message": message} if success else {"error": message})


def handle_api_students_remove(handler, data):
    """POST /api/students/remove - Remove student."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        handler._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
        return

    student_code_to_remove = data.get('code')
    if not student_code_to_remove:
        handler._send_response(400, {"error": "Missing 'code' of student configuration to remove"})
        return

    success = False
    message = "Failed to remove student configuration."
    status_code = 500

    with data_lock:
        original_len = len(students_data_store)
        students_data_store[:] = [s_config for s_config in students_data_store if s_config.get('code') != student_code_to_remove]

        if len(students_data_store) < original_len:
            if save_students_data_to_db():
                success = True
                message = f"Student configuration with code '{student_code_to_remove}' removed successfully."
                status_code = 200
            else:
                message = f"Student configuration with code '{student_code_to_remove}' removed from memory, but FAILED to save to file."
                status_code = 500
        else:
            message = f"Student configuration with code '{student_code_to_remove}' not found."
            status_code = 404

    handler._send_response(status_code, {"success": success, "message": message} if success else {"error": message})


def handle_api_student_update_counting_class(handler, data):
    """POST /api/student/update-counting-class - Update counting assignment."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        handler._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
        return

    student_code_to_update = data.get('student_code')
    class_to_update = data.get('class_name')
    is_counting = data.get('is_counting')

    if not student_code_to_update or not class_to_update or is_counting is None:
        handler._send_response(400, {"error": "Missing student_code, class_name, or is_counting status."})
        return

    success = False
    message = "Failed to update student's counting classes."
    status_code = 500
    student_note_for_message = "Unknown"

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
                current_counts_set.discard(class_to_update)

            sorted_list_of_classes = sorted(list(current_counts_set))
            new_counts_classes_str = f"[{', '.join(sorted_list_of_classes)}]" if sorted_list_of_classes else "[]"

            target_student_config['counts_classes_str'] = new_counts_classes_str

            if save_students_data_to_db():
                success = True
                action = "added to" if is_counting else "removed from"
                message = f"Class '{class_to_update}' {action} student '{student_note_for_message}'s counting list."
                status_code = 200
            else:
                message = f"Failed to save updated counting list for student '{student_note_for_message}' to file."
                status_code = 500

    handler._send_response(status_code, {"success": success, "message": message} if success else {"error": message})


# =============================================================================
# Count Data Endpoints
# =============================================================================

def handle_api_increment(handler, data):
    """POST /api/increment - Increment count."""
    class_name = data.get('className')
    type_val = data.get('type')
    points_val = data.get('points')
    day_identifier = data.get('day')

    # Basic validation
    if not all([class_name, type_val, points_val is not None, day_identifier]):
        handler._send_response(400, {"error": "Missing data: className, type, points, or day"})
        return
    if type_val not in ['student', 'teacher']:
        handler._send_response(400, {"error": "Invalid type"})
        return
    if not isinstance(points_val, int) or not (0 <= points_val <= 6):
        handler._send_response(400, {"error": "Invalid points value"})
        return
    if day_identifier.lower() not in ['monday', 'tuesday', 'wednesday']:
        handler._send_response(400, {"error": "Invalid day. Must be one of monday, tuesday, wednesday"})
        return

    # Student Authorization Check
    cookies = handler.get_cookies()
    student_auth_cookie = cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
    if student_auth_cookie:
        student_code = student_auth_cookie.value
        if not is_student_allowed(student_code, class_name, day_identifier.lower()):
            handler._send_response(403, {"error": "Forbidden: You are not authorized to modify counts for this class/day."})
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
            handler._send_response(200, {"success": True, "message": f"Count incremented for {day_identifier}"})
        else:
            handler._send_response(500, {"error": "Failed to save to database"})
    except Exception as e:
        print(f"Error during increment: {e}")
        traceback.print_exc()
        handler._send_response(500, {"error": "Internal server error"})


def handle_api_decrement(handler, data):
    """POST /api/decrement - Decrement count."""
    class_name = data.get('className')
    type_val = data.get('type')
    points_val = data.get('points')
    day_identifier = data.get('day')

    # Basic validation
    if not all([class_name, type_val, points_val is not None, day_identifier]):
        handler._send_response(400, {"error": "Missing data: className, type, points, or day"})
        return
    if type_val not in ['student', 'teacher']:
        handler._send_response(400, {"error": "Invalid type"})
        return
    if not isinstance(points_val, int) or not (0 <= points_val <= 6):
        handler._send_response(400, {"error": "Invalid points value"})
        return
    if day_identifier.lower() not in ['monday', 'tuesday', 'wednesday']:
        handler._send_response(400, {"error": "Invalid day. Must be one of monday, tuesday, wednesday"})
        return

    # Student Authorization Check
    cookies = handler.get_cookies()
    student_auth_cookie = cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
    if student_auth_cookie:
        student_code = student_auth_cookie.value
        if not is_student_allowed(student_code, class_name, day_identifier.lower()):
            handler._send_response(403, {"error": "Forbidden: You are not authorized to modify counts for this class/day."})
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
            handler._send_response(200, {"success": True, "message": f"Count decremented for {day_identifier}"})
        else:
            handler._send_response(500, {"error": "Failed to save to database"})
    except Exception as e:
        print(f"Error during decrement: {e}")
        traceback.print_exc()
        handler._send_response(500, {"error": "Internal server error"})


# =============================================================================
# Configuration Endpoints
# =============================================================================

def handle_api_data_save_config(handler, data):
    """POST /api/data/save/config - Save configuration."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role != ADMIN_ROLE:
        handler._send_response(403, {"error": "Forbidden: Administrator access required."})
        return

    oauth_eneabled = data.get('oauth_eneabled')
    allowed_domains = data.get('allowed_oauth_domains')

    if oauth_eneabled is None or not isinstance(allowed_domains, list):
        handler._send_response(400, {"error": "Invalid payload. 'oauth_eneabled' (string) and 'allowed_oauth_domains' (list) are required."})
        return

    if oauth_eneabled not in ["true", "false"]:
        handler._send_response(400, {"error": "'oauth_eneabled' must be the string 'true' or 'false'."})
        return

    if save_main_config_to_json(data):
        handler._send_response(200, {"message": "OAuth configuration saved successfully."})
    else:
        handler._send_response(500, {"error": "Failed to save OAuth configuration to file."})


def handle_api_language_set(handler, data):
    """POST /api/language/set - Set language preference."""
    language_code = data.get('language')

    if language_code not in ['cs', 'en']:
        handler._send_response(400, {"error": "Invalid language code. Must be 'cs' or 'en'."})
        return

    # Set cookie to expire in 1 year
    max_age_1_year = 365 * 24 * 60 * 60
    language_cookie_headers = create_cookies(
        LANGUAGE_COOKIE_NAME,
        language_code,
        path='/',
        max_age=max_age_1_year,
        httponly=False
    )

    handler.send_response(200)
    handler.send_header('Content-type', 'application/json')
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
    handler.send_header('Access-Control-Allow-Credentials', 'true')

    for header_name, header_value in language_cookie_headers:
        handler.send_header(header_name, header_value)

    handler.end_headers()
    response_payload = {"success": True, "message": f"Language set to {language_code}"}
    handler.wfile.write(json.dumps(response_payload).encode('utf-8'))
    print(f"Language cookie set to '{language_code}'.")


# =============================================================================
# Route Mapping
# =============================================================================

POST_ROUTES = {
    '/login': handle_login,
    '/login/student': handle_login_student,
    '/logout': handle_logout,
    '/api/auth/change': handle_auth_change,
    '/api/users': handle_api_users_post,
    '/api/users/remove': handle_api_users_remove,
    '/api/users/set': handle_api_users_set,
    '/api/users/reset': handle_api_users_set,  # Alias
    '/api/classes/add': handle_api_classes_add,
    '/api/classes/remove': handle_api_classes_remove,
    '/api/classes/update_counts': handle_api_classes_update_counts,
    '/api/classes/update_iscountedby': handle_api_classes_update_iscountedby,
    '/api/students/add': handle_api_students_add,
    '/api/students/remove': handle_api_students_remove,
    '/api/student/update-counting-class': handle_api_student_update_counting_class,
    '/api/increment': handle_api_increment,
    '/api/decrement': handle_api_decrement,
    '/api/data/save/config': handle_api_data_save_config,
    '/api/language/set': handle_api_language_set,
}
