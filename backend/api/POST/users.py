
from auth import get_current_user_info
from data_manager import user_password_store, save_user_data_to_db
from config import ADMIN_ROLE, DEFAULT_ROLE_FOR_NEW_USERS


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
