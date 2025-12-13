"""GET /api/classes endpoint handler."""

from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME
from auth import get_current_user_info
from data_manager import class_data_store, data_lock


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
