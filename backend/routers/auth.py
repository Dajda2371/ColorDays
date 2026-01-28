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
    generate_token, store_token, hash_password
)
from data_manager import user_password_store, data_lock, students_data_store, save_user_data_to_db
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

def set_cookie_headers(response: Response, headers: list):
    """Helper to append Set-Cookie headers from utils to FastAPI response."""
    for header_name, header_value in headers:
        if header_name.lower() == 'set-cookie':
            response.headers.append('set-cookie', header_value)

def is_user_using_oauth(username: str) -> bool:
    user_data = user_password_store.get(username)
    if user_data and user_data.get('password_hash') == '_GOOGLE_AUTH_USER_':
        return True
    return False

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

@router.get("/login/google")
def login_google(response: Response, oauth_modules=Depends(get_google_oauth_modules)):
    InstalledAppFlow, _ = oauth_modules

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI
        )
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        return RedirectResponse(auth_url)
    except FileNotFoundError:
        return JSONResponse(status_code=500, content={"error": "Google OAuth configuration error (server-side)."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Could not initiate Google login."})

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
