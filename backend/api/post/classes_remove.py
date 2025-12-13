
from auth import get_current_user_info
from data_manager import class_data_store, data_lock, save_class_data_to_db
from config import ADMIN_ROLE


def handle_api_classes_remove(handler, data):
    """POST /api/classes/remove - Remove class."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role != ADMIN_ROLE:
        handler._send_response(403, {"error": "Forbidden: Administrator access required."})
        return

    class_name_to_remove = data.get('class')
    if not class_name_to_remove:
        handler._send_response(400, {"error": "Missing class name to remove"})
        return

    success = False
    message = "Failed to remove class."
    status_code = 500

    with data_lock:
        original_len = len(class_data_store)
        class_data_store[:] = [c for c in class_data_store if c['class'] != class_name_to_remove]
        if len(class_data_store) < original_len:
            if save_class_data_to_db():
                success = True
                message = f"Class '{class_name_to_remove}' removed successfully."
                status_code = 200
            else:
                message = f"Class '{class_name_to_remove}' removed from memory, but FAILED to save to file."
                status_code = 500
        else:
            message = f"Class '{class_name_to_remove}' not found."
            status_code = 404

    if success:
        handler._send_response(status_code, {"success": True, "message": message})
    else:
        handler._send_response(status_code, {"error": message})
