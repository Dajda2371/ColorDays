from fastapi import Request, HTTPException, Depends, status
from typing import Optional, Tuple, Dict
from config import (
    SQL_COOKIE_NAME,
    GOOGLE_COOKIE_NAME,
    USERNAME_COOKIE_NAME,
    DEFAULT_ROLE_FOR_NEW_USERS,
    ADMIN_ROLE,
    SESSION_COOKIE_NAME,
    VALID_SESSION_VALUE
)
from data_manager import user_password_store

# --- Google OAuth Imports (Optional) ---
try:
    from google_auth_oauthlib.flow import InstalledAppFlow, Flow
    from googleapiclient import discovery as google_discovery_service
    GOOGLE_OAUTH_AVAILABLE = True
except ImportError:
    InstalledAppFlow = None
    google_discovery_service = None
    GOOGLE_OAUTH_AVAILABLE = False

# Global store for active sessions (token -> username)
active_sessions: Dict[str, str] = {}

def get_google_oauth_modules():
    if not GOOGLE_OAUTH_AVAILABLE:
        raise HTTPException(status_code=500, detail="Google OAuth libraries not available")
    return InstalledAppFlow, google_discovery_service

def get_current_user_info(request: Request) -> Tuple[Optional[str], Optional[str]]:
    """
    Retrieves the authenticated user's key and role from cookies.
    """
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)

    is_valid_session = False
    if session_cookie:
        if session_cookie == VALID_SESSION_VALUE:
            is_valid_session = True
        elif session_cookie in active_sessions:
            is_valid_session = True

    if not is_valid_session:
        return None, None

    username_key_in_store = None
    sql_auth_cookie = request.cookies.get(SQL_COOKIE_NAME)
    if sql_auth_cookie and sql_auth_cookie in user_password_store:
        username_key_in_store = sql_auth_cookie

    if not username_key_in_store:
        google_auth_cookie = request.cookies.get(GOOGLE_COOKIE_NAME)
        if google_auth_cookie and google_auth_cookie in user_password_store:
            username_key_in_store = google_auth_cookie

    if not username_key_in_store:
        username_cookie = request.cookies.get(USERNAME_COOKIE_NAME)
        if username_cookie and username_cookie in user_password_store:
            username_key_in_store = username_cookie

    if username_key_in_store:
        user_data = user_password_store.get(username_key_in_store)
        if user_data:
            return username_key_in_store, user_data.get('role', DEFAULT_ROLE_FOR_NEW_USERS)

    return None, None

def get_current_user(request: Request):
    user, role = get_current_user_info(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return {"username": user, "role": role}

def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != ADMIN_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrator access required."
        )
    return current_user
