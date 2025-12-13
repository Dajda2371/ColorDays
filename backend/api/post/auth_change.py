
import json

from auth import get_current_user_info, is_user_using_oauth
from data_manager import user_password_store, data_lock, save_user_data_to_db
from utils import hash_password, create_cookie_clear_headers, verify_password
from config import CHANGE_PASSWORD_COOKIE_NAME


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
