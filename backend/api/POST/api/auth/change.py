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


@router.post("/api/auth/change")
def change_password(
    data: ChangePasswordRequest,
    response: Response,
    request: Request,
    user_info=Depends(get_current_user_info)
):
    user_key, _ = user_info

    if not user_key:
        return JSONResponse(status_code=401, content={"error": "Authentication error: User identity not found."})

    if is_user_using_oauth(user_key):
        return JSONResponse(status_code=403, content={"error": "Password change not allowed for Google OAuth users."})

    old_password = data.oldPassword
    new_password = data.newPassword

    verification_needed = True
    if request.cookies.get(CHANGE_PASSWORD_COOKIE_NAME):
        verification_needed = False

    message = "Failed to change password."
    status_code = 500
    save_needed = False

    with data_lock:
        stored_user_data = user_password_store.get(user_key)

        if not stored_user_data:
            return JSONResponse(status_code=404, content={"error": f"User '{user_key}' not found."})

        if verification_needed:
            is_old_valid, _ = verify_password(stored_user_data, old_password, user_key)
            if not is_old_valid:
                return JSONResponse(status_code=401, content={"error": "Old password verification failed."})

        try:
            hashed_pw = hash_password(new_password)
            user_password_store[user_key]['password_hash'] = hashed_pw
            save_needed = True
        except Exception as e:
             return JSONResponse(status_code=500, content={"error": "Server error during password hashing."})

        if save_needed:
            if save_user_data_to_db():
                message = f"Password for user '{user_key}' changed successfully."
                status_code = 200
            else:
                 return JSONResponse(status_code=500, content={"error": f"Password changed in memory for '{user_key}', but FAILED to save to file."})

    # Success
    extra_headers_on_success = []
    if request.cookies.get(CHANGE_PASSWORD_COOKIE_NAME):
        clear_headers = create_cookie_clear_headers(CHANGE_PASSWORD_COOKIE_NAME, path='/')
        extra_headers_on_success.extend(clear_headers)

    set_cookie_headers(response, extra_headers_on_success)
    return {"success": True, "message": message}
