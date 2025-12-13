
import traceback
import collections

from config import SQL_AUTH_USER_STUDENT_COOKIE_NAME
from data_manager import load_counts_from_db, save_counts_to_db, is_student_allowed


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
