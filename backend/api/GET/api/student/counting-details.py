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


@router.get("/api/student/counting-details")
def get_student_counting_details(
    code: str,
    day: str,
    request: Request,
    user_info=Depends(get_current_user_info)
):
    user_key, user_role = user_info

    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    is_logged_in = False
    if session_cookie and (session_cookie == VALID_SESSION_VALUE or session_cookie in active_sessions):
         is_logged_in = True

    if not is_logged_in:
        raise HTTPException(status_code=401, detail="Authentication required")

    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    if day not in ['1', '2', '3']:
        raise HTTPException(status_code=400, detail="Invalid 'day' parameter. Must be 1, 2, or 3.")

    with data_lock:
        target_student = next((s for s in students_data_store if s.get('code') == code), None)

        if not target_student:
             raise HTTPException(status_code=404, detail=f"Student configuration with code '{code}' not found.")

        student_main_class = target_student.get('class')
        if not student_main_class:
             raise HTTPException(status_code=500, detail=f"Student with code '{code}' has no class assigned.")

        is_counted_by_field = f"iscountedby{day}"
        response_payload = []

        counts_str = target_student.get('counts_classes', '[]')
        student_personal_counts_set = set()
        try:
             if counts_str.startswith('[') and counts_str.endswith(']'):
                 content = counts_str[1:-1]
                 if content.strip():
                     student_personal_counts_set = {c.strip() for c in content.split(',') if c.strip()}
        except:
            pass

        for class_being_evaluated in class_data_store:
            if class_being_evaluated.get(is_counted_by_field) == student_main_class:
                class_to_display_name = class_being_evaluated['class']
                student_is_counting_this_class = class_to_display_name in student_personal_counts_set
                also_counted_by_notes = []

                for other_student in students_data_store:
                    if other_student.get('code') == code:
                        continue

                    other_counts_str = other_student.get('counts_classes', '[]')
                    try:
                        if other_counts_str.startswith('[') and other_counts_str.endswith(']'):
                             other_content = other_counts_str[1:-1]
                             if other_content.strip():
                                 if class_to_display_name in {c.strip() for c in other_content.split(',') if c.strip()}:
                                     also_counted_by_notes.append(other_student.get('note', 'Unknown Note'))
                    except:
                        pass

                response_payload.append({
                    "class_name": class_to_display_name,
                    "is_counted_by_current_student": student_is_counting_this_class,
                    "also_counted_by_notes": sorted(list(set(also_counted_by_notes)))
                })

        final_response = {
            "student_note": target_student.get('note', ''),
            "student_class": target_student.get('class', ''),
            "counting_details": sorted(response_payload, key=lambda x: x['class_name'])
        }

    return final_response
