
import json
import traceback

from utils import store_token, create_cookies, generate_token, verify_password
from data_manager import user_password_store
from config import (
    USERNAME_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    SQL_COOKIE_NAME,
    DEFAULT_ROLE_FOR_NEW_USERS,
)


def handle_login(handler):
    """POST /login - Username/password login."""
    content_length = int(handler.headers.get('Content-Length', 0))
    if content_length == 0:
        handler._send_response(400, {"error": "Missing request body for login"})
        return

    try:
        post_body_bytes = handler.rfile.read(content_length)
        credentials = json.loads(post_body_bytes)
        username = credentials.get('username')
        submitted_password = credentials.get('password')
        print(f"DEBUG: Login attempt for username: '{username}'")

        # Initialize login result and extra headers
        login_successful = False
        extra_cookie_headers = []

        stored_info = user_password_store.get(username)

        if stored_info and submitted_password:
            login_successful, extra_cookie_headers = verify_password(stored_info, submitted_password, username)
            if not login_successful:
                print(f"Password verification failed for user: {username}")
        elif not stored_info:
            print(f"Login attempt failed: Username '{username}' not found.")
        elif not submitted_password:
            print(f"Login attempt failed: No password provided for user '{username}'.")

        if login_successful:
            # Prepare the standard cookies
            cleaned_username = username.strip('"') if username else ""
            user_cookie_headers = create_cookies(USERNAME_COOKIE_NAME, cleaned_username, path='/', httponly=False)

            # Generate a secure session token
            session_token = generate_token(64)
            store_token(username, session_token, handler.client_address[0] if hasattr(handler, 'client_address') else '_NULL_')
            handler.__class__.active_sessions[session_token] = username
            session_cookie_headers = create_cookies(SESSION_COOKIE_NAME, session_token, path='/')

            sql_user_cookie_headers = create_cookies(SQL_COOKIE_NAME, username, path='/', httponly=False)

            all_cookie_headers = user_cookie_headers + session_cookie_headers + extra_cookie_headers + sql_user_cookie_headers

            # Send response headers manually
            handler.send_response(200)
            handler.send_header('Content-type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
            handler.send_header('Access-Control-Allow-Credentials', 'true')

            print(f"DEBUG: Preparing to send {len(all_cookie_headers)} cookie(s)...")
            for header_name, header_value in all_cookie_headers:
                handler.send_header(header_name, header_value)
                print(f"DEBUG: Sent {header_name} header: {header_value}")

            handler.end_headers()

            # Include role in login response
            role = user_password_store.get(username, {}).get('role', DEFAULT_ROLE_FOR_NEW_USERS)

            response_payload = {
                "success": True,
                "message": "Login successful",
                "username": cleaned_username,
                "role": role
            }
            response_body = json.dumps(response_payload).encode('utf-8')
            handler.wfile.write(response_body)

            print(f"Login successful for user: {username}, {len(all_cookie_headers)} session/other cookie(s) sent.")

        else:
            handler._send_response(401, {"error": "Invalid username or password"})

    except json.JSONDecodeError:
        print("Error: Invalid JSON received for login.")
        handler._send_response(400, {"error": "Invalid JSON format in request body"})
    except Exception as e:
        print(f"Error during login processing: {e}")
        print(traceback.format_exc())
        handler._send_response(500, {"error": "Server error during login"})
