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


@router.post("/api/students/remove")
def remove_student(data: StudentRemoveRequest, request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info
    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    student_code = data.code

    with data_lock:
        original_len = len(students_data_store)
        new_store = [s for s in students_data_store if s.get('code') != student_code]

        if len(new_store) < original_len:
            students_data_store[:] = new_store
            if save_students_data_to_db():
                return {"success": True, "message": f"Student configuration with code '{student_code}' removed successfully."}
            else:
                 raise HTTPException(status_code=500, detail=f"Student configuration with code '{student_code}' removed from memory, but FAILED to save to file.")
        else:
             raise HTTPException(status_code=404, detail=f"Student configuration with code '{student_code}' not found.")
