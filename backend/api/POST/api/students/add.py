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


@router.post("/api/students/add")
def add_student(data: StudentAddRequest, request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info
    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    student_class = data.class_
    note = data.note

    with data_lock:
        new_student_config = {
            "code": generate_random_code(),
            "class": student_class,
            "note": note,
            "counts_classes": "[]" # Using counts_classes to match DB schema
        }
        students_data_store.append(new_student_config)
        students_data_store.sort(key=lambda x: (x['class'], x.get('note', '')))

        if save_students_data_to_db():
            return {"success": True, "message": f"Student configuration for class '{student_class}' (Note: '{note}') added successfully."}
        else:
             try:
                 students_data_store.remove(new_student_config)
             except:
                 pass
             raise HTTPException(status_code=500, detail=f"Failed to save new student configuration for '{student_class}' (Note: '{note}') to file.")
