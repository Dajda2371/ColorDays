from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from dependencies import get_current_admin_user
from data_manager import students_data_store, data_lock, save_students_data_to_db
from utils import generate_random_code

router = APIRouter()

class StudentAddRequest(BaseModel):
    class_: str = Field(..., alias="class")
    note: str

@router.post("/api/students")
def add_student(payload: StudentAddRequest, admin_user: dict = Depends(get_current_admin_user)):
    class_name = payload.class_
    note = payload.note
    
    if not class_name:
        raise HTTPException(status_code=400, detail="Class name required.")

    code = generate_random_code(5) 

    with data_lock:
        new_student = {
            "code": code,
            "class": class_name,
            "note": note,
            "counts_classes": "[]"
        }
        students_data_store.append(new_student)
        
        if save_students_data_to_db():
            return {"success": True, "message": "Student added.", "code": code}
        else:
            students_data_store.pop()
            raise HTTPException(status_code=500, detail="Failed to save student data.")
