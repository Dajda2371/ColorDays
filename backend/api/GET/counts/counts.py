"""GET /api/counts endpoint handler."""

import urllib.parse

from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME
from auth import get_current_user_info
from data_manager import load_counts_from_db, is_student_allowed


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
