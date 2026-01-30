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


@router.get("/oauth2callback")
def oauth2callback(request: Request, response: Response, oauth_modules=Depends(get_google_oauth_modules)):
    InstalledAppFlow, google_discovery_service = oauth_modules
    code = request.query_params.get('code')

    if not code:
        return JSONResponse(status_code=400, content={"error": "Missing authorization code from Google."})

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials

        userinfo_service = google_discovery_service.build('oauth2', 'v2', credentials=credentials)
        user_info = userinfo_service.userinfo().get().execute()

        _user_email_from_google = user_info.get('email')
        user_email = _user_email_from_google.strip('"') if _user_email_from_google else None

        if not user_email:
             return JSONResponse(status_code=400, content={"error": "Could not retrieve email from Google."})

        user_name_from_google_raw = user_info.get('name', _user_email_from_google)
        profile_picture = user_info.get('picture')

        name_for_cookie = ''
        if user_email:
            name_for_cookie = user_email.split('@', 1)[0]
        elif user_name_from_google_raw:
            name_for_cookie = user_name_from_google_raw.strip('"')

        with data_lock:
            if user_email not in user_password_store:
                user_password_store[user_email] = {
                    'password_hash': '_GOOGLE_AUTH_USER_',
                    'profile_picture_url': profile_picture if profile_picture else '_NULL_',
                    'role': DEFAULT_ROLE_FOR_NEW_USERS
                }
                save_user_data_to_db()

        all_cookies = (
            create_cookies(USERNAME_COOKIE_NAME, name_for_cookie, path='/', httponly=False) +
            create_cookies(SESSION_COOKIE_NAME, VALID_SESSION_VALUE, path='/') +
            create_cookie_clear_headers(CHANGE_PASSWORD_COOKIE_NAME, path='/') +
            create_cookies(GOOGLE_COOKIE_NAME, user_email, path='/', httponly=False)
        )

        # We need to redirect to /menu.html, but also set cookies.
        # RedirectResponse can have headers.

        redirect_response = RedirectResponse(url='/menu.html')
        set_cookie_headers(redirect_response, all_cookies)
        return redirect_response

    except Exception as e:
        print(f"OAuth error: {e}")
        return JSONResponse(status_code=500, content={"error": "Google OAuth callback failed."})
