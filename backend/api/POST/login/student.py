from fastapi import APIRouter, Response, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from config import (
    CLIENT_SECRETS_FILE, GOOGLE_SCOPES, GOOGLE_REDIRECT_URI,
    USERNAME_COOKIE_NAME, SESSION_COOKIE_NAME, SQL_COOKIE_NAME,
    CHANGE_PASSWORD_COOKIE_NAME, GOOGLE_COOKIE_NAME, SQL_AUTH_USER_STUDENT_COOKIE_NAME,
    VALID_SESSION_VALUE, DEFAULT_ROLE_FOR_NEW_USERS
)
from utils import (
    verify_password, create_cookies, create_cookie_clear_headers,
    generate_token, store_token, hash_password, set_cookie_headers
)
from data_manager import (
    user_password_store, data_lock, students_data_store,
    save_user_data_to_db, is_user_using_oauth
)
from dependencies import get_current_user_info, get_google_oauth_modules, active_sessions


router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str


class StudentLoginRequest(BaseModel):
    code: str


class ChangePasswordRequest(BaseModel):
    oldPassword: str
    newPassword: str


@router.post("/login/student")
def login_student(credentials: StudentLoginRequest, response: Response):
    student_code = credentials.code

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
        set_cookie_headers(response, all_cookie_headers)

        return {
            "success": True,
            "message": "Student login successful",
            "note": student_note,
            "class": found_student.get('class')
        }
    else:
        return JSONResponse(status_code=401, content={"error": "Invalid student code"})
