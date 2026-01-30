
from auth import get_current_user_info
from data_manager import students_data_store, data_lock, save_students_data_to_db
from config import ADMIN_ROLE, TEACHER_ROLE


def handle_api_students_remove(handler, data):
    """POST /api/students/remove - Remove student."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        handler._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
        return

    student_code_to_remove = data.get('code')
    if not student_code_to_remove:
        handler._send_response(400, {"error": "Missing 'code' of student configuration to remove"})
        return

    success = False
    message = "Failed to remove student configuration."
    status_code = 500

    with data_lock:
        original_len = len(students_data_store)
        students_data_store[:] = [s_config for s_config in students_data_store if s_config.get('code') != student_code_to_remove]

        if len(students_data_store) < original_len:
            if save_students_data_to_db():
                success = True
                message = f"Student configuration with code '{student_code_to_remove}' removed successfully."
                status_code = 200
            else:
                message = f"Student configuration with code '{student_code_to_remove}' removed from memory, but FAILED to save to file."
                status_code = 500
        else:
            message = f"Student configuration with code '{student_code_to_remove}' not found."
            status_code = 404

    handler._send_response(status_code, {"success": success, "message": message} if success else {"error": message})
