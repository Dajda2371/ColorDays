from fastapi import APIRouter, Depends, Request
from dependencies import get_current_user_info
from config import SQL_AUTH_USER_STUDENT_COOKIE_NAME

router = APIRouter()

@router.get("/api/auth/me")
def get_me(request: Request):
    user_key, user_role = get_current_user_info(request)
    
    is_student = False
    if request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME):
        is_student = True
        
    return {
        "username": user_key,
        "role": user_role,
        "is_student": is_student
    }
