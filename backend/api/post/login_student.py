
import json
import traceback

from utils import create_cookies
from data_manager import students_data_store, data_lock
from config import (
    SESSION_COOKIE_NAME,
    VALID_SESSION_VALUE,
    USERNAME_COOKIE_NAME,
    SQL_AUTH_USER_STUDENT_COOKIE_NAME,
)


def handle_login_student(handler):
    """POST /login/student - Student code login."""
    content_length = int(handler.headers.get('Content-Length', 0))
    if content_length == 0:
        handler._send_response(400, {"error": "Missing request body for student login"})
        return

    try:
        post_body_bytes = handler.rfile.read(content_length)
        credentials = json.loads(post_body_bytes)
        student_code = credentials.get('code')
        print(f"DEBUG: Student login attempt with code: '{student_code}'")

        if not student_code:
            handler._send_response(400, {"error": "Missing student code"})
            return

        found_student = None
        with data_lock:
            for student_item in students_data_store:
                if student_item.get('code') == student_code:
                    found_student = student_item
                    break

        if found_student:
            student_note = found_student.get('note', 'Student')
            student_actual_code = found_student.get('code')

            session_cookie_headers = create_cookies(SESSION_COOKIE_NAME, VALID_SESSION_VALUE, path='/')
            user_cookie_headers = create_cookies(USERNAME_COOKIE_NAME, student_note, path='/', httponly=False)
            student_auth_cookie_headers = create_cookies(SQL_AUTH_USER_STUDENT_COOKIE_NAME, student_actual_code, path='/', httponly=False)

            all_cookie_headers = session_cookie_headers + user_cookie_headers + student_auth_cookie_headers

            handler.send_response(200)
            handler.send_header('Content-type', 'application/json')
            # Get the origin from the request, or use localhost as fallback
            origin = handler.headers.get('Origin', 'http://localhost:8000')
            handler.send_header('Access-Control-Allow-Origin', origin)
            handler.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
            handler.send_header('Access-Control-Allow-Credentials', 'true')

            for header_name, header_value in all_cookie_headers:
                handler.send_header(header_name, header_value)

            handler.end_headers()
            response_payload = {"success": True, "message": "Student login successful", "note": student_note, "class": found_student.get('class')}
            handler.wfile.write(json.dumps(response_payload).encode('utf-8'))
            print(f"Student login successful for code: {student_actual_code} (Note: {student_note}). Cookies sent.")
        else:
            handler._send_response(401, {"error": "Invalid student code"})

    except json.JSONDecodeError:
        handler._send_response(400, {"error": "Invalid JSON format in request body"})
    except Exception as e:
        print(f"Error during student login processing: {e}\n{traceback.format_exc()}")
        handler._send_response(500, {"error": "Server error during student login"})
