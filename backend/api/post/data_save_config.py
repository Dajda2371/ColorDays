
from auth import get_current_user_info
from data_manager import save_main_config_to_json
from config import ADMIN_ROLE


def handle_api_data_save_config(handler, data):
    """POST /api/data/save/config - Save configuration."""
    user_key, user_role = get_current_user_info(handler)

    if not handler.is_logged_in() or user_role != ADMIN_ROLE:
        handler._send_response(403, {"error": "Forbidden: Administrator access required."})
        return

    oauth_eneabled = data.get('oauth_eneabled')
    allowed_domains = data.get('allowed_oauth_domains')

    if oauth_eneabled is None or not isinstance(allowed_domains, list):
        handler._send_response(400, {"error": "Invalid payload. 'oauth_eneabled' (string) and 'allowed_oauth_domains' (list) are required."})
        return

    if oauth_eneabled not in ["true", "false"]:
        handler._send_response(400, {"error": "'oauth_eneabled' must be the string 'true' or 'false'."})
        return

    if save_main_config_to_json(data):
        handler._send_response(200, {"message": "OAuth configuration saved successfully."})
    else:
        handler._send_response(500, {"error": "Failed to save OAuth configuration to file."})
