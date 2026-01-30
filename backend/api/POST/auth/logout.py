from fastapi import APIRouter, Response
from config import (
    SESSION_COOKIE_NAME,
    USERNAME_COOKIE_NAME,
    SQL_COOKIE_NAME,
    GOOGLE_COOKIE_NAME,
    SQL_AUTH_USER_STUDENT_COOKIE_NAME,
    CHANGE_PASSWORD_COOKIE_NAME,
)

router = APIRouter()

@router.post("/logout")
def logout(response: Response):
    cookies_to_clear = [
        SESSION_COOKIE_NAME,
        USERNAME_COOKIE_NAME,
        SQL_COOKIE_NAME,
        GOOGLE_COOKIE_NAME,
        SQL_AUTH_USER_STUDENT_COOKIE_NAME,
        CHANGE_PASSWORD_COOKIE_NAME
    ]
    for cookie_name in cookies_to_clear:
         response.delete_cookie(key=cookie_name, path='/')
    
    return {"message": "Logged out successfully"}
