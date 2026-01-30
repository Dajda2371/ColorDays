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


@router.post("/login")
def login(credentials: LoginRequest, response: Response):
    username = credentials.username
    submitted_password = credentials.password

    login_successful = False
    extra_cookie_headers = []

    stored_info = user_password_store.get(username)

    if stored_info and submitted_password:
        login_successful, extra_cookie_headers = verify_password(stored_info, submitted_password, username)

    if login_successful:
        cleaned_username = username.strip('"') if username else ""

        # We can use utils.create_cookies or FastAPI set_cookie.
        # Since utils returns headers, let's use the helper.
        user_cookie_headers = create_cookies(USERNAME_COOKIE_NAME, cleaned_username, path='/', httponly=False)

        session_token = generate_token(64)
        store_token(username, session_token) # ip is optional
        active_sessions[session_token] = username
        session_cookie_headers = create_cookies(SESSION_COOKIE_NAME, session_token, path='/')

        sql_user_cookie_headers = create_cookies(SQL_COOKIE_NAME, username, path='/', httponly=False)

        all_cookie_headers = user_cookie_headers + session_cookie_headers + extra_cookie_headers + sql_user_cookie_headers

        set_cookie_headers(response, all_cookie_headers)

        role = stored_info.get('role', DEFAULT_ROLE_FOR_NEW_USERS)

        return {
            "success": True,
            "message": "Login successful",
            "username": cleaned_username,
            "role": role
        }
    else:
        # Instead of 401 with error content, returning JSON as per original behavior might be preferred by frontend?
        # Original: handler._send_response(401, {"error": "Invalid username or password"})
        return JSONResponse(status_code=401, content={"error": "Invalid username or password"})
