"""GET /api/students and /api/student/counting-details endpoint handlers."""

import urllib.parse

from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME
from auth import get_current_user_info
from data_manager import students_data_store, class_data_store, data_lock


def handle_api_students(handler):
    """GET /api/students - List all students."""
    user_key, user_role = get_current_user_info(handler)
    cookies = handler.get_cookies()

    if not handler.is_logged_in():
        handler._send_response(401, {"error": "Authentication required"})
        return

    student_auth_cookie = cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
    is_student_user_session = student_auth_cookie is not None

    response_payload = []
    with data_lock:
        if is_student_user_session:
            student_code_from_cookie = student_auth_cookie.value
            found_student_data_item = None
            for s_data_item in students_data_store:
                if s_data_item.get('code') == student_code_from_cookie:
                    found_student_data_item = s_data_item
                    break

            if found_student_data_item:
                counting_classes_list = []
                try:
                    s_str = found_student_data_item.get('counts_classes_str', '[]')
                    if s_str.startswith('[') and s_str.endswith(']'):
                        s_content = s_str[1:-1]
                        if s_content.strip():
                            counting_classes_list = [item.strip() for item in s_content.split(',')]
                except Exception as e:
                    print(f"Error parsing counts_classes_str: {e}")

                response_payload.append({**found_student_data_item, "counting_classes": counting_classes_list})

        else:
            if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
                handler._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
                return

            for student_data_item in students_data_store:
                counting_classes_list = []
                try:
                    s_str = student_data_item.get('counts_classes_str', '[]')
                    if s_str.startswith('[') and s_str.endswith(']'):
                        s_content = s_str[1:-1]
                        if s_content.strip():
                            counting_classes_list = [item.strip() for item in s_content.split(',')]
                except Exception as e:
                    print(f"Error parsing counts_classes_str: {e}")
                response_payload.append({**student_data_item, "counting_classes": counting_classes_list})

    handler._send_response(200, response_payload)


def handle_api_student_counting_details(handler):
    """GET /api/student/counting-details - Get student counting details."""
    user_key, user_role = get_current_user_info(handler)
    parsed_path = urllib.parse.urlparse(handler.path)
    query = urllib.parse.parse_qs(parsed_path.query)

    if not handler.is_logged_in():
        handler._send_response(401, {"error": "Authentication required"})
        return
    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        handler._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
        return

    student_code_param = query.get('code', [None])[0]
    day_param_str = query.get('day', [None])[0]

    if not student_code_param or not day_param_str:
        handler._send_response(400, {"error": "Missing 'code' or 'day' query parameter."})
        return
    if day_param_str not in ['1', '2', '3']:
        handler._send_response(400, {"error": "Invalid 'day' parameter. Must be 1, 2, or 3."})
        return

    target_student_config = None
    with data_lock:
        for s_config in students_data_store:
            if s_config.get('code') == student_code_param:
                target_student_config = s_config
                break

        if not target_student_config:
            handler._send_response(404, {"error": f"Student configuration with code '{student_code_param}' not found."})
            return

        student_main_class_name = target_student_config.get('class')
        if not student_main_class_name:
            handler._send_response(500, {"error": f"Student with code '{student_code_param}' has no class assigned."})
            return

        is_counted_by_field = f"iscountedby{day_param_str}"
        response_payload = []

        target_student_personal_counts_str = target_student_config.get('counts_classes_str', '[]')
        student_personal_counts_set = set()
        try:
            if target_student_personal_counts_str.startswith('[') and target_student_personal_counts_str.endswith(']'):
                content = target_student_personal_counts_str[1:-1]
                if content.strip():
                    student_personal_counts_set = {c.strip() for c in content.split(',') if c.strip()}
        except Exception:
            pass

        for class_being_evaluated in class_data_store:
            if class_being_evaluated.get(is_counted_by_field) == student_main_class_name:
                class_to_display_name = class_being_evaluated['class']
                student_is_counting_this_class = class_to_display_name in student_personal_counts_set
                also_counted_by_notes = []
                for other_student_config in students_data_store:
                    if other_student_config.get('code') == student_code_param:
                        continue
                    other_student_counts_classes_str = other_student_config.get('counts_classes_str', '[]')
                    try:
                        if other_student_counts_classes_str.startswith('[') and other_student_counts_classes_str.endswith(']'):
                            other_content = other_student_counts_classes_str[1:-1]
                            if other_content.strip():
                                if class_to_display_name in {c.strip() for c in other_content.split(',') if c.strip()}:
                                    also_counted_by_notes.append(other_student_config.get('note', 'Unknown Note'))
                    except Exception:
                        pass

                response_payload.append({
                    "class_name": class_to_display_name,
                    "is_counted_by_current_student": student_is_counting_this_class,
                    "also_counted_by_notes": sorted(list(set(also_counted_by_notes)))
                })

        final_api_response = {
            "student_note": target_student_config.get('note', ''),
            "student_class": target_student_config.get('class', ''),
            "counting_details": sorted(response_payload, key=lambda x: x['class_name'])
        }

    handler._send_response(200, final_api_response)
