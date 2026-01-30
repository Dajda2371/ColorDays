from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from config import (
    CLIENT_SECRETS_FILE,
    GOOGLE_SCOPES,
    GOOGLE_REDIRECT_URI,
    USERNAME_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    CHANGE_PASSWORD_COOKIE_NAME,
    GOOGLE_COOKIE_NAME,
    VALID_SESSION_VALUE,
    DEFAULT_ROLE_FOR_NEW_USERS,
)
from data_manager import user_password_store, data_lock, save_user_data_to_db
import backend.api.get.auth.oauth as oauth_mod

router = APIRouter()

@router.get("/oauth2callback")
def oauth2callback(code: str = None):
    try:
        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code from Google.")

        if oauth_mod.InstalledAppFlow is None or oauth_mod.google_discovery_service is None:
            raise HTTPException(status_code=500, detail="Google OAuth components missing on server.")

        flow = oauth_mod.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials

        userinfo_service = oauth_mod.google_discovery_service.build('oauth2', 'v2', credentials=credentials)
        user_info = userinfo_service.userinfo().get().execute()

        _user_email_from_google = user_info.get('email')
        user_email = _user_email_from_google.strip('"') if _user_email_from_google else None

        user_name_from_google_raw = user_info.get('name', _user_email_from_google)
        profile_picture = user_info.get('picture')

        name_for_cookie = ''
        if user_email:
            name_for_cookie = user_email.split('@', 1)[0]
        elif user_name_from_google_raw:
            name_for_cookie = user_name_from_google_raw.strip('"')

        if not user_email:
             raise HTTPException(status_code=400, detail="Could not retrieve email from Google.")

        with data_lock:
            if user_email not in user_password_store:
                user_password_store[user_email] = {
                    'password_hash': '_GOOGLE_AUTH_USER_',
                    'profile_picture_url': profile_picture if profile_picture else '_NULL_',
                    'role': DEFAULT_ROLE_FOR_NEW_USERS
                }
                save_user_data_to_db()

        response = RedirectResponse(url='/menu.html')
        
        response.set_cookie(key=USERNAME_COOKIE_NAME, value=name_for_cookie, path='/', httponly=False)
        response.set_cookie(key=SESSION_COOKIE_NAME, value=VALID_SESSION_VALUE, path='/', httponly=True)
        response.delete_cookie(key=CHANGE_PASSWORD_COOKIE_NAME, path='/')
        response.set_cookie(key=GOOGLE_COOKIE_NAME, value=user_email, path='/', httponly=False)

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Google OAuth callback failed.")
