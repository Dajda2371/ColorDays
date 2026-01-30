from fastapi import APIRouter, Depends, HTTPException, Request
from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME
from dependencies import get_current_user_info
from data_manager import class_data_store, data_lock

router = APIRouter()

@router.get("/api/classes")
def get_classes(request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info

    # Access cookie directly from request
    is_student_session = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME) is not None

    if not user_key and not is_student_session:
         raise HTTPException(status_code=401, detail="Authentication required")

    if not (user_role in [ADMIN_ROLE, TEACHER_ROLE] or is_student_session):
        raise HTTPException(status_code=403, detail="Forbidden: Access to this resource is restricted for your account type.")

    with data_lock:
        response_data = list(class_data_store)
    return response_data
