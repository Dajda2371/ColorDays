
from auth import get_current_user_info
from data_manager import class_data_store, data_lock, save_class_data_to_db
from config import ADMIN_ROLE


def handle_api_classes_add(handler, data):
    """POST /api/classes/add - Add class."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role != ADMIN_ROLE:
        handler._send_response(403, {"error": "Forbidden: Administrator access required."})
        return

    class_name = data.get('class')
    teacher = data.get('teacher')
    counts1 = data.get('counts1', 'F')
    counts2 = data.get('counts2', 'F')
    counts3 = data.get('counts3', 'F')
    iscountedby1 = data.get('iscountedby1', '_NULL_')
    iscountedby2 = data.get('iscountedby2', '_NULL_')
    iscountedby3 = data.get('iscountedby3', '_NULL_')

    if not class_name or not teacher:
        handler._send_response(400, {"error": "Missing class name or teacher"})
        return

    if counts1 not in ['T', 'F'] or counts2 not in ['T', 'F'] or counts3 not in ['T', 'F']:
        handler._send_response(400, {"error": "Invalid counts values (must be T or F)"})
        return

    success = False
    message = "Failed to add class."
    status_code = 500

    with data_lock:
        if any(c['class'] == class_name for c in class_data_store):
            message = f"Class '{class_name}' already exists."
            status_code = 409
        else:
            new_class = {
                "class": class_name, "teacher": teacher,
                "counts1": counts1, "counts2": counts2, "counts3": counts3,
                "iscountedby1": iscountedby1, "iscountedby2": iscountedby2,
                "iscountedby3": iscountedby3
            }
            class_data_store.append(new_class)
            class_data_store.sort(key=lambda x: x['class'])
            if save_class_data_to_db():
                success = True
                message = f"Class '{class_name}' added successfully."
                status_code = 201
            else:
                class_data_store.pop()
                message = f"Failed to save class '{class_name}' to file."
                status_code = 500

    if success:
        handler._send_response(status_code, {"success": True, "message": message})
    else:
        handler._send_response(status_code, {"error": message})
