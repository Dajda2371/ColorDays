"""GET /login/google endpoint handler."""

from config import (
    CLIENT_SECRETS_FILE,
    GOOGLE_SCOPES,
    GOOGLE_REDIRECT_URI,
)
import backend.api.get.oauth as oauth_mod

def handle_login_google(handler):
    """GET /login/google - Initiate Google OAuth flow."""
    try:
        if oauth_mod.InstalledAppFlow is None:
            handler._send_response(500, {"error": "Google OAuth component (InstalledAppFlow) missing on server."})
            return

        flow = oauth_mod.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI
        )
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

        handler.send_response(302)
        handler.send_header('Location', auth_url)
        handler.end_headers()
    except FileNotFoundError:
        handler._send_response(500, {"error": "Google OAuth configuration error (server-side)."})
    except Exception as e:
        handler._send_response(500, {"error": "Could not initiate Google login."})
