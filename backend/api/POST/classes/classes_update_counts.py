
from auth import get_current_user_info
from data_manager import class_data_store, data_lock, save_class_data_to_db
from config import ADMIN_ROLE


def handle_api_classes_update_counts(handler, data):
    """POST /api/classes/update_counts - Update counting days."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role != ADMIN_ROLE:
        handler._send_response(403, {"error": "Forbidden: Administrator access required."})
        return

    class_name = data.get('class')
    count_field = data.get('countField')
    new_value = data.get('value')

    if not all([class_name, count_field, new_value is not None]):
        handler._send_response(400, {"error": "Missing class, countField, or value"})
        return

    valid_count_fields = ["counts1", "counts2", "counts3"]
    if count_field not in valid_count_fields:
        handler._send_response(400, {"error": f"Invalid countField. Must be one of {valid_count_fields}"})
        return

    if new_value not in ['T', 'F']:
        handler._send_response(400, {"error": "Invalid value. Must be 'T' or 'F'"})
        return

    success = False
    message = "Failed to update class count."
    status_code = 500

    with data_lock:
        class_to_update = next((cls_item for cls_item in class_data_store if cls_item['class'] == class_name), None)

        if not class_to_update:
            message = f"Class '{class_name}' not found."
            status_code = 404
        else:
            class_to_update[count_field] = new_value
            if save_class_data_to_db():
                success = True
                message = f"Count '{count_field}' for class '{class_name}' updated to '{new_value}'."
                status_code = 200
            else:
                message = f"Count for class '{class_name}' updated in memory, but FAILED to save to file. Consider restarting server or checking file permissions."
                status_code = 500

    if success:
        handler._send_response(status_code, {"success": True, "message": message})
    else:
        handler._send_response(status_code, {"error": message})
