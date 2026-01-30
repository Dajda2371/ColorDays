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


@router.post("/logout")
def logout(response: Response):
    session_clear_headers = create_cookie_clear_headers(SESSION_COOKIE_NAME, path='/')
    user_clear_headers = create_cookie_clear_headers(USERNAME_COOKIE_NAME, path='/')
    change_pw_clear_headers = create_cookie_clear_headers(CHANGE_PASSWORD_COOKIE_NAME, path='/')
    sql_user_clear_headers = create_cookie_clear_headers(SQL_COOKIE_NAME, path='/')
    google_auth_clear_headers = create_cookie_clear_headers(GOOGLE_COOKIE_NAME, path='/')
    sql_student_auth_clear_headers = create_cookie_clear_headers(SQL_AUTH_USER_STUDENT_COOKIE_NAME, path='/')

    all_clear_headers = (session_clear_headers + user_clear_headers + change_pw_clear_headers +
                         sql_user_clear_headers + google_auth_clear_headers + sql_student_auth_clear_headers)

    set_cookie_headers(response, all_clear_headers)

    return {"success": True, "message": "Logged out successfully"}
