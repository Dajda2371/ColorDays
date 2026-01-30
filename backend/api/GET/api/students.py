from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME, SESSION_COOKIE_NAME, VALID_SESSION_VALUE
from data_manager import students_data_store, class_data_store, data_lock, save_students_data_to_db
from dependencies import get_current_user_info, active_sessions
from utils import generate_random_code


router = APIRouter()

class StudentAddRequest(BaseModel):
    class_: str = Field(..., alias="class")
    note: Optional[str] = ""


class StudentRemoveRequest(BaseModel):
    code: str


class StudentUpdateCountingClassRequest(BaseModel):
    student_code: str
    class_name: str
    is_counting: bool


@router.get("/api/students")
def list_students(request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info
    student_cookie = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)

    # Check session
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    is_logged_in = False
    if session_cookie:
        if session_cookie == VALID_SESSION_VALUE:
            is_logged_in = True
        elif session_cookie in active_sessions:
            is_logged_in = True

    if not is_logged_in:
        raise HTTPException(status_code=401, detail="Authentication required")

    is_student_user_session = student_cookie is not None

    response_payload = []
    with data_lock:
        if is_student_user_session:
             student_code = student_cookie
             found_student = next((s for s in students_data_store if s.get('code') == student_code), None)

             if found_student:
                 counting_classes_list = []
                 try:
                     s_str = found_student.get('counts_classes', '[]')
                     if s_str.startswith('[') and s_str.endswith(']'):
                         s_content = s_str[1:-1]
                         if s_content.strip():
                             counting_classes_list = [item.strip() for item in s_content.split(',')]
                 except Exception:
                     pass

                 response_payload.append({**found_student, "counting_classes": counting_classes_list})

        else:
            if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
                raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

            for student_data_item in students_data_store:
                counting_classes_list = []
                try:
                    s_str = student_data_item.get('counts_classes', '[]')
                    if s_str.startswith('[') and s_str.endswith(']'):
                        s_content = s_str[1:-1]
                        if s_content.strip():
                             counting_classes_list = [item.strip() for item in s_content.split(',')]
                except Exception:
                     pass
                response_payload.append({**student_data_item, "counting_classes": counting_classes_list})

    return response_payload
