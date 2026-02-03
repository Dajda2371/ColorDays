from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from config import ADMIN_ROLE, TEACHER_ROLE
from dependencies import get_current_user_info
from data_manager import students_data_store, data_lock, save_students_data_to_db

router = APIRouter()

class StudentUpdateCountingRequest(BaseModel):
    student_code: str
    class_name: str
    is_counting: bool

@router.put("/api/student/counting-class")
def update_student_counting_class(payload: StudentUpdateCountingRequest, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info
    
    if not user_key:
         raise HTTPException(status_code=401, detail="Authentication required")
    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
         raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    student_code = payload.student_code
    class_name = payload.class_name
    is_counting = payload.is_counting

    with data_lock:
        target_student_config = next((s for s in students_data_store if s.get('code') == student_code), None)
        if not target_student_config:
            raise HTTPException(status_code=404, detail=f"Student configuration with code '{student_code}' not found.")

        student_note = target_student_config.get('note', student_code)
        
        counts_str = target_student_config.get('counts_classes', '[]') 
        current_counts_set = set()
        if counts_str.startswith('[') and counts_str.endswith(']'):
            content = counts_str[1:-1]
            if content.strip():
                current_counts_set = {c.strip() for c in content.split(',') if c.strip()}

        if is_counting:
            current_counts_set.add(class_name)
        else:
            current_counts_set.discard(class_name)

        sorted_list = sorted(list(current_counts_set))
        new_counts_str = f"[{', '.join(sorted_list)}]" if sorted_list else "[]"

        target_student_config['counts_classes'] = new_counts_str

        if save_students_data_to_db():
            action = "added to" if is_counting else "removed from"
            return {"success": True, "message": f"Class '{class_name}' {action} student '{student_note}'s counting list."}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to save updated counting list for student '{student_note}'.")
