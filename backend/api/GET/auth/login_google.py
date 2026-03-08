from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from config import (
    CLIENT_SECRETS_FILE,
    GOOGLE_SCOPES,
    GOOGLE_REDIRECT_URI,
)
from dependencies import Flow

router = APIRouter()

@router.get("/login/google")
def login_google():
    try:
        from dependencies import Flow
        if Flow is None:
             raise HTTPException(status_code=500, detail="Google OAuth component (Flow) missing on server.")

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=GOOGLE_SCOPES, redirect_uri=GOOGLE_REDIRECT_URI
        )
        auth_url, state = flow.authorization_url(prompt='consent', access_type='offline')

        response = RedirectResponse(auth_url)
        # Store the code verifier in a cookie to satisfy PKCE requirements on callback
        if hasattr(flow, 'code_verifier') and flow.code_verifier:
            response.set_cookie(key="google_oauth_code_verifier", value=flow.code_verifier, httponly=True, secure=True, samesite='lax')
        
        return response
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Google OAuth configuration error (server-side).")
    except Exception as e:
        print(f"Error in login_google: {e}")
        raise HTTPException(status_code=500, detail=f"Could not initiate Google login: {e}")
