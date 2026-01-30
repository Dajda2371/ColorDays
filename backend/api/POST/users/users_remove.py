
from auth import get_current_user_info
from data_manager import user_password_store, data_lock, save_user_data_to_db
from config import ADMIN_ROLE


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
