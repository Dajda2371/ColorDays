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


@router.post("/api/student/update-counting-class")
def update_counting_class(data: StudentUpdateCountingClassRequest, request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info

    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
         raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    student_code = data.student_code
    class_name = data.class_name
    is_counting = data.is_counting

    with data_lock:
        target_student = next((s for s in students_data_store if s.get('code') == student_code), None)

        if not target_student:
             raise HTTPException(status_code=404, detail=f"Student configuration with code '{student_code}' not found.")

        student_note = target_student.get('note', student_code)
        counts_str = target_student.get('counts_classes', '[]')
        current_counts_set = set()

        try:
            if counts_str.startswith('[') and counts_str.endswith(']'):
                content = counts_str[1:-1]
                if content.strip():
                    current_counts_set = {c.strip() for c in content.split(',') if c.strip()}
        except:
            pass

        if is_counting:
            current_counts_set.add(class_name)
        else:
            current_counts_set.discard(class_name)

        sorted_list = sorted(list(current_counts_set))
        new_counts_str = f"[{', '.join(sorted_list)}]" if sorted_list else "[]"

        target_student['counts_classes'] = new_counts_str

        if save_students_data_to_db():
            action = "added to" if is_counting else "removed from"
            return {"success": True, "message": f"Class '{class_name}' {action} student '{student_note}'s counting list."}
        else:
             raise HTTPException(status_code=500, detail=f"Failed to save updated counting list for student '{student_note}' to file.")
