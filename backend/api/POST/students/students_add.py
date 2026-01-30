
from auth import get_current_user_info
from data_manager import students_data_store, data_lock, save_students_data_to_db
from utils import generate_random_code
from config import ADMIN_ROLE, TEACHER_ROLE


def handle_api_students_add(handler, data):
    """POST /api/students/add - Add student."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        handler._send_response(403, {"error": "Forbidden: Administrator access required."})
        return

    student_class = data.get('class')
    note = data.get('note', '')

    if not student_class:
        handler._send_response(400, {"error": "Missing 'class' for the new student configuration."})
        return

    success = False
    message = "Failed to add student configuration."
    status_code = 500

    with data_lock:
        new_student_config = {
            "code": generate_random_code(),
            "class": student_class,
            "note": note,
            "counts_classes_str": "[]"
        }
        students_data_store.append(new_student_config)
        students_data_store.sort(key=lambda x: (x['class'], x.get('note', '')))

        if save_students_data_to_db():
            success = True
            message = f"Student configuration for class '{student_class}' (Note: '{note}') added successfully."
            status_code = 201
        else:
            students_data_store.pop()
            message = f"Failed to save new student configuration for '{student_class}' (Note: '{note}') to file."
            status_code = 500

    handler._send_response(status_code, {"success": success, "message": message} if success else {"error": message})
