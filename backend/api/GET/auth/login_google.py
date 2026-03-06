from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from config import (
    CLIENT_SECRETS_FILE,
    GOOGLE_SCOPES,
    GOOGLE_REDIRECT_URI,
)
from dependencies import InstalledAppFlow

router = APIRouter()

@router.get("/login/google")
def login_google():
    try:
        if InstalledAppFlow is None:
             raise HTTPException(status_code=500, detail="Google OAuth component (InstalledAppFlow) missing on server.")

        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI
        )
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

        return RedirectResponse(auth_url)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Google OAuth configuration error (server-side).")
    except Exception as e:
        print(f"Error in login_google: {e}")
        raise HTTPException(status_code=500, detail=f"Could not initiate Google login: {e}")
