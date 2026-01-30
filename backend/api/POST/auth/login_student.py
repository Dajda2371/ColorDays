from fastapi import APIRouter, HTTPException, Response, Body
from pydantic import BaseModel
from data_manager import students_data_store, data_lock
from config import (
    SESSION_COOKIE_NAME,
    VALID_SESSION_VALUE,
    USERNAME_COOKIE_NAME,
    SQL_AUTH_USER_STUDENT_COOKIE_NAME,
)

router = APIRouter()

class StudentLoginRequest(BaseModel):
    code: str

@router.post("/login/student")
def login_student(response: Response, payload: StudentLoginRequest = Body(...)):
    student_code = payload.code

    found_student = None
    with data_lock:
        for student_item in students_data_store:
            if student_item.get('code') == student_code:
                found_student = student_item
                break

    if found_student:
        student_note = found_student.get('note', 'Student')
        student_actual_code = found_student.get('code')

        response.set_cookie(key=SESSION_COOKIE_NAME, value=VALID_SESSION_VALUE, path='/', httponly=True)
        response.set_cookie(key=USERNAME_COOKIE_NAME, value=student_note, path='/', httponly=False)
        response.set_cookie(key=SQL_AUTH_USER_STUDENT_COOKIE_NAME, value=student_actual_code, path='/', httponly=False)

        return {
            "success": True, 
            "message": "Student login successful", 
            "note": student_note, 
            "class": found_student.get('class')
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid student code")
