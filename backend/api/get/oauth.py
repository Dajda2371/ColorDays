"""GET /login/google and /oauth2callback endpoint handlers."""

import urllib.parse

from config import (
    CLIENT_SECRETS_FILE,
    GOOGLE_SCOPES,
    GOOGLE_REDIRECT_URI,
    USERNAME_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    CHANGE_PASSWORD_COOKIE_NAME,
    GOOGLE_COOKIE_NAME,
    VALID_SESSION_VALUE,
    DEFAULT_ROLE_FOR_NEW_USERS,
)
from data_manager import user_password_store, data_lock, save_user_data_to_db
from utils import create_cookies, create_cookie_clear_headers

# These will be set by server.py if available
InstalledAppFlow = None
google_discovery_service = None


def set_oauth_dependencies(installed_app_flow, discovery_service):
    """Set OAuth dependencies from server.py.

    Args:
        installed_app_flow: The InstalledAppFlow class from google_auth_oauthlib
        discovery_service: The discovery module from googleapiclient
    """
    global InstalledAppFlow, google_discovery_service
    InstalledAppFlow = installed_app_flow
    google_discovery_service = discovery_service


def handle_login_google(handler):
    """GET /login/google - Initiate Google OAuth flow."""
    try:
        if InstalledAppFlow is None:
            handler._send_response(500, {"error": "Google OAuth component (InstalledAppFlow) missing on server."})
            return

        flow = InstalledAppFlow.from_client_secrets_file(
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


def handle_oauth2callback(handler):
    """GET /oauth2callback - Handle Google OAuth callback."""
    parsed_path = urllib.parse.urlparse(handler.path)
    query = urllib.parse.parse_qs(parsed_path.query)

    try:
        code = query.get('code', [None])[0]
        if not code:
            handler._send_response(400, {"error": "Missing authorization code from Google."})
            return

        if InstalledAppFlow is None or google_discovery_service is None:
            handler._send_response(500, {"error": "Google OAuth components missing on server."})
            return

        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials

        userinfo_service = google_discovery_service.build('oauth2', 'v2', credentials=credentials)
        user_info = userinfo_service.userinfo().get().execute()

        _user_email_from_google = user_info.get('email')
        user_email = _user_email_from_google.strip('"') if _user_email_from_google else None

        user_name_from_google_raw = user_info.get('name', _user_email_from_google)
        profile_picture = user_info.get('picture')

        name_for_cookie = ''
        if user_email:
            name_for_cookie = user_email.split('@', 1)[0]
        elif user_name_from_google_raw:
            name_for_cookie = user_name_from_google_raw.strip('"')

        if not user_email:
            handler._send_response(400, {"error": "Could not retrieve email from Google."})
            return

        with data_lock:
            if user_email not in user_password_store:
                user_password_store[user_email] = {
                    'password_hash': '_GOOGLE_AUTH_USER_',
                    'profile_picture_url': profile_picture if profile_picture else '_NULL_',
                    'role': DEFAULT_ROLE_FOR_NEW_USERS
                }
                save_user_data_to_db()

        all_cookies = create_cookies(USERNAME_COOKIE_NAME, name_for_cookie, path='/', httponly=False) + \
                      create_cookies(SESSION_COOKIE_NAME, VALID_SESSION_VALUE, path='/') + \
                      create_cookie_clear_headers(CHANGE_PASSWORD_COOKIE_NAME, path='/') + \
                      create_cookies(GOOGLE_COOKIE_NAME, user_email, path='/', httponly=False)

        handler.send_response(302)
        handler.send_header('Location', '/menu.html')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
        handler.send_header('Access-Control-Allow-Credentials', 'true')

        for header_name, header_value in all_cookies:
            handler.send_header(header_name, header_value)

        handler.end_headers()
    except Exception as e:
        handler._send_response(500, {"error": "Google OAuth callback failed."})
