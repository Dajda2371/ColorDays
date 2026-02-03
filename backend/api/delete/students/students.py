from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from dependencies import get_current_admin_user
from data_manager import students_data_store, data_lock, save_students_data_to_db

router = APIRouter()



@router.delete("/api/students")
def remove_student(code: str, admin_user: dict = Depends(get_current_admin_user)):
    
    with data_lock:
        found_student = next((s for s in students_data_store if s['code'] == code), None)
        if not found_student:
             raise HTTPException(status_code=404, detail="Student not found.")
        
        students_data_store.remove(found_student)
        
        if save_students_data_to_db():
            return {"success": True, "message": "Student removed."}
        else:
            students_data_store.append(found_student)
            raise HTTPException(status_code=500, detail="Failed to save student removal.")
