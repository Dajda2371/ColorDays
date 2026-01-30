
from auth import get_current_user_info, is_user_using_oauth
from data_manager import user_password_store, data_lock, save_user_data_to_db
from config import ADMIN_ROLE


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
