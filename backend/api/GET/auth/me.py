from fastapi import APIRouter, Depends, Request
from dependencies import get_current_user_info
from config import SQL_AUTH_USER_STUDENT_COOKIE_NAME
from data_manager import is_user_using_oauth

router = APIRouter()

@router.get("/api/auth/me")
def get_me(request: Request):
    user_key, user_role = get_current_user_info(request)
    
    is_student = False
    if request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME):
        is_student = True
        
    is_oauth = False
    if user_key:
        is_oauth = is_user_using_oauth(user_key)
        
    return {
        "username": user_key,
        "role": user_role,
        "is_student": is_student,
        "is_oauth_user": is_oauth
    }
