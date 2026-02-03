from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from config import ADMIN_ROLE
from dependencies import get_current_admin_user
from data_manager import class_data_store, data_lock, save_class_data_to_db, students_data_store, save_students_data_to_db
import json

router = APIRouter()



@router.delete("/api/classes")
def remove_class(class_name: str = Query(..., alias="class"), admin_user: dict = Depends(get_current_admin_user)):
    
    with data_lock:
        found_class = next((c for c in class_data_store if c['class'] == class_name), None)
        if not found_class:
             raise HTTPException(status_code=404, detail=f"Class '{class_name}' not found.")
        
        class_data_store.remove(found_class)
        
        if save_class_data_to_db():
            # Cleanup students
            students_modified = False
            for student in students_data_store:
                try:
                    counts_list_str = student.get('counts_classes', '[]')
                    try:
                        personal_counts = json.loads(counts_list_str)
                        if not isinstance(personal_counts, list):
                             personal_counts = []
                    except json.JSONDecodeError:
                        personal_counts = []

                    if class_name in personal_counts:
                        personal_counts = [c for c in personal_counts if c != class_name]
                        student['counts_classes'] = json.dumps(personal_counts)
                        students_modified = True
                except Exception as e:
                    print(f"Error checking student {student.get('code')} for removed class: {e}")
            
            if students_modified:
                save_students_data_to_db()

            return {"success": True, "message": f"Class '{class_name}' removed successfully."}
        else:
            class_data_store.append(found_class)
            class_data_store.sort(key=lambda x: x['class'])
            raise HTTPException(status_code=500, detail=f"Failed to save removal of class '{class_name}'.")
