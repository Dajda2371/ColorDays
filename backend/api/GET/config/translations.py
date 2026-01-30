"""GET /api/translations endpoint handler."""

from config import TRANSLATIONS_FILE_PATH


def handle_api_translations(handler):
    """GET /api/translations - Get language translations."""
    if TRANSLATIONS_FILE_PATH.is_file():
        try:
            with open(TRANSLATIONS_FILE_PATH, 'rb') as f:
                content = f.read()
            handler._send_response(200, data=content, content_type='application/json')
        except Exception as e:
            handler._send_response(500, {"error": f"Error serving translations file: {e}"}, content_type='application/json')
    else:
        handler._send_response(404, {"error": "Translations file not found."}, content_type='application/json')
