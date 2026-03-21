from fastapi import APIRouter, HTTPException, Depends, Response, Body
from pydantic import BaseModel
from config import (
    SESSION_COOKIE_NAME,
    VALID_SESSION_VALUE,
    USERNAME_COOKIE_NAME,
    SQL_COOKIE_NAME,
    CHANGE_PASSWORD_COOKIE_NAME,
)
from utils import verify_password
from data_manager import user_password_store, data_lock

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(response: Response, login_data: LoginRequest = Body(...)):
    username = login_data.username.strip()
    password = login_data.password

    is_valid = False
    extra_cookies = []

    with data_lock:
        stored_user_data = user_password_store.get(username)
        if stored_user_data:
            is_valid, extra_cookies, force_change = verify_password(stored_user_data, password, username)
        else:
            force_change = False

    if is_valid:
        # Set cookies
        response.set_cookie(key=SESSION_COOKIE_NAME, value=VALID_SESSION_VALUE, path='/', httponly=True)
        response.set_cookie(key=USERNAME_COOKIE_NAME, value=username, path='/', httponly=False)
        response.set_cookie(key=SQL_COOKIE_NAME, value=username, path='/', httponly=True)

        for name, value_header in extra_cookies:
            # Check for the specific change-password value string from utils logic
            if "change-password=not-required" in value_header:
                response.set_cookie(key=CHANGE_PASSWORD_COOKIE_NAME, value="not-required", path='/', httponly=False)

        return {"success": True, "message": "Login successful", "force_change": force_change}
    else:
        raise HTTPException(status_code=401, detail="Invalid username or password")
