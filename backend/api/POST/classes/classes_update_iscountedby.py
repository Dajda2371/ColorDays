
import json

from auth import get_current_user_info
from data_manager import class_data_store, data_lock, save_class_data_to_db
from config import ADMIN_ROLE, TEACHER_ROLE, DATA_DIR


def handle_api_classes_update_iscountedby(handler, data):
    """POST /api/classes/update_iscountedby - Update counting assignments."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        handler._send_response(403, {"error": "Forbidden: Administrator or Teacher access required."})
        return

    class_name_to_update = data.get('class')
    day_identifier = data.get('dayIdentifier')
    new_value = data.get('value')

    if not all([class_name_to_update, day_identifier, new_value is not None]):
        handler._send_response(400, {"error": "Missing class, dayIdentifier, or value"})
        return

    if day_identifier not in ['1', '2', '3']:
        handler._send_response(400, {"error": "Invalid dayIdentifier. Must be '1', '2', or '3'."})
        return

    field_to_update = f"iscountedby{day_identifier}"

    # Server-side check for can_students_count_their_own_class
    allow_self_count_str = 'true'
    config_file_path = DATA_DIR / 'config.json'
    try:
        if config_file_path.is_file():
            with open(config_file_path, 'r', encoding='utf-8') as f:
                current_config_on_disk = json.load(f)
            allow_self_count_str = current_config_on_disk.get('can_students_count_their_own_class', 'true')
            print(f"DEBUG: Read 'can_students_count_their_own_class' from disk: {allow_self_count_str}")
        else:
            print(f"Warning: {config_file_path} not found during iscountedby update. Defaulting 'can_students_count_their_own_class' to 'true'.")
    except json.JSONDecodeError:
        print(f"!!! ERROR: Invalid JSON in {config_file_path} during iscountedby update. Defaulting 'can_students_count_their_own_class' to 'true'.")
    except Exception as e:
        print(f"!!! ERROR reading {config_file_path} during iscountedby update: {e}. Defaulting 'can_students_count_their_own_class' to 'true'.")

    allow_self_count = allow_self_count_str.lower() == 'true'

    if not allow_self_count and new_value == class_name_to_update:
        handler._send_response(400, {"error": f"Configuration prevents class '{class_name_to_update}' from counting itself."})
        return

    success = False
    message = "Failed to update class counting assignment."
    status_code = 500

    with data_lock:
        class_found = False
        for cls_item in class_data_store:
            if cls_item['class'] == class_name_to_update:
                cls_item[field_to_update] = new_value
                class_found = True
                break

        if not class_found:
            message = f"Class '{class_name_to_update}' not found."
            status_code = 404
        else:
            if save_class_data_to_db():
                success = True
                message = f"Assignment for class '{class_name_to_update}' on day {day_identifier} updated to '{new_value}' and saved."
                status_code = 200
            else:
                message = f"Assignment for class '{class_name_to_update}' updated in memory, but FAILED to save to file."
                status_code = 500

    if success:
        handler._send_response(status_code, {"success": True, "message": message})
    else:
        handler._send_response(status_code, {"error": message})
