"""GET /api/users endpoint handler."""

from config import ADMIN_ROLE, DEFAULT_ROLE_FOR_NEW_USERS
from data_manager import user_password_store, data_lock


def handle_api_users(handler):
    """GET /api/users - List all users."""
    if not handler.is_logged_in():
        handler._send_response(401, {"error": "Authentication required"})
        return

    handler.handle_get_users()
