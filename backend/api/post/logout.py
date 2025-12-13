
import json

from utils import create_cookie_clear_headers
from config import (
    SESSION_COOKIE_NAME,
    USERNAME_COOKIE_NAME,
    CHANGE_PASSWORD_COOKIE_NAME,
    SQL_COOKIE_NAME,
    GOOGLE_COOKIE_NAME,
    SQL_AUTH_USER_STUDENT_COOKIE_NAME,
)

def handle_logout(handler):
    """POST /logout - Logout and clear session."""
    print("Logout request received. Preparing cookie clearing headers.")

    session_clear_headers = create_cookie_clear_headers(SESSION_COOKIE_NAME, path='/')
    user_clear_headers = create_cookie_clear_headers(USERNAME_COOKIE_NAME, path='/')
    change_pw_clear_headers = create_cookie_clear_headers(CHANGE_PASSWORD_COOKIE_NAME, path='/')
    sql_user_clear_headers = create_cookie_clear_headers(SQL_COOKIE_NAME, path='/')
    google_auth_clear_headers = create_cookie_clear_headers(GOOGLE_COOKIE_NAME, path='/')
    sql_student_auth_clear_headers = create_cookie_clear_headers(SQL_AUTH_USER_STUDENT_COOKIE_NAME, path='/')
    all_clear_headers = session_clear_headers + user_clear_headers + change_pw_clear_headers + sql_user_clear_headers + google_auth_clear_headers + sql_student_auth_clear_headers

    handler.send_response(200)
    handler.send_header('Content-type', 'application/json')
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
    handler.send_header('Access-Control-Allow-Credentials', 'true')

    print(f"DEBUG: Preparing to send {len(all_clear_headers)} cookie clearing header(s)...")
    for header_name, header_value in all_clear_headers:
        handler.send_header(header_name, header_value)
        print(f"DEBUG: Sent Set-Cookie expiration header: {header_value}")

    handler.end_headers()

    response_body = json.dumps({"success": True, "message": "Logged out successfully"}).encode('utf-8')
    handler.wfile.write(response_body)

    print("Logout successful, cookie expiration headers sent.")
