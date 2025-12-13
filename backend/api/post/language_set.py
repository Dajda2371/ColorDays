
import json

from utils import create_cookies
from config import LANGUAGE_COOKIE_NAME


def handle_api_language_set(handler, data):
    """POST /api/language/set - Set language preference."""
    language_code = data.get('language')

    if language_code not in ['cs', 'en']:
        handler._send_response(400, {"error": "Invalid language code. Must be 'cs' or 'en'."})
        return

    # Set cookie to expire in 1 year
    max_age_1_year = 365 * 24 * 60 * 60
    language_cookie_headers = create_cookies(
        LANGUAGE_COOKIE_NAME,
        language_code,
        path='/',
        max_age=max_age_1_year,
        httponly=False
    )

    handler.send_response(200)
    handler.send_header('Content-type', 'application/json')
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
    handler.send_header('Access-Control-Allow-Credentials', 'true')

    for header_name, header_value in language_cookie_headers:
        handler.send_header(header_name, header_value)

    handler.end_headers()
    response_payload = {"success": True, "message": f"Language set to {language_code}"}
    handler.wfile.write(json.dumps(response_payload).encode('utf-8'))
    print(f"Language cookie set to '{language_code}'.")
