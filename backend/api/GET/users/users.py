"""GET /api/users endpoint handler."""

from config import ADMIN_ROLE, DEFAULT_ROLE_FOR_NEW_USERS
from data_manager import user_password_store, data_lock
from auth import get_current_user_info


def handle_api_users(handler):
    """GET /api/users - List all users with details."""
    if not handler.is_logged_in():
        handler._send_response(401, {"error": "Authentication required"})
        return

    # RBAC Check
    _user_key, user_role = get_current_user_info(handler)
    if user_role != ADMIN_ROLE:
        handler._send_response(403, {"error": "Forbidden: Administrator access required."})
        return

    # Build user list with password status and role
    user_list = []
    with data_lock:
        for username_key, user_data_val in user_password_store.items():
            password_hash = user_data_val['password_hash']
            role = user_data_val.get('role', DEFAULT_ROLE_FOR_NEW_USERS)

            # Determine password status for frontend
            status = "set"  # Default
            if password_hash is None or password_hash.upper() == '_NULL_':
                status = "not_set"
            elif password_hash == '_GOOGLE_AUTH_USER_':
                status = "google_auth_user"
            elif password_hash == 'NOT_SET':
                status = "not_set"
            # Check for pre-generated passwords like _password_
            elif password_hash.startswith('_') and password_hash.endswith('_') and \
                 password_hash.upper() != '_NULL_' and password_hash.upper() != '_GOOGLE_AUTH_USER_':
                status = password_hash[1:-1]  # Extract the pre-generated password

            user_list.append({
                "username": username_key,
                "password": status,  # 'password' field name for frontend compatibility
                "role": role
            })

    handler.send_json(user_list)
