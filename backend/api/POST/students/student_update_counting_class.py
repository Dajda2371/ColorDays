
from auth import get_current_user_info
from data_manager import students_data_store, data_lock, save_students_data_to_db
from config import ADMIN_ROLE, TEACHER_ROLE


def handle_api_student_update_counting_class(handler, data):
    """POST /api/student/update-counting-class - Update counting assignment."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        handler._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
        return

    student_code_to_update = data.get('student_code')
    class_to_update = data.get('class_name')
    is_counting = data.get('is_counting')

    if not student_code_to_update or not class_to_update or is_counting is None:
        handler._send_response(400, {"error": "Missing student_code, class_name, or is_counting status."})
        return

    success = False
    message = "Failed to update student's counting classes."
    status_code = 500
    student_note_for_message = "Unknown"

    with data_lock:
        target_student_config = next((s for s in students_data_store if s.get('code') == student_code_to_update), None)

        if not target_student_config:
            message = f"Student configuration with code '{student_code_to_update}' not found."
            status_code = 404
        else:
            student_note_for_message = target_student_config.get('note', student_code_to_update)
            counts_str = target_student_config.get('counts_classes_str', '[]')
            current_counts_set = set()
            if counts_str.startswith('[') and counts_str.endswith(']'):
                content = counts_str[1:-1]
                if content.strip():
                    current_counts_set = {c.strip() for c in content.split(',') if c.strip()}

            if is_counting:
                current_counts_set.add(class_to_update)
            else:
                current_counts_set.discard(class_to_update)

            sorted_list_of_classes = sorted(list(current_counts_set))
            new_counts_classes_str = f"[{', '.join(sorted_list_of_classes)}]" if sorted_list_of_classes else "[]"

            target_student_config['counts_classes_str'] = new_counts_classes_str

            if save_students_data_to_db():
                success = True
                action = "added to" if is_counting else "removed from"
                message = f"Class '{class_to_update}' {action} student '{student_note_for_message}'s counting list."
                status_code = 200
            else:
                message = f"Failed to save updated counting list for student '{student_note_for_message}' to file."
                status_code = 500

    handler._send_response(status_code, {"success": success, "message": message} if success else {"error": message})
