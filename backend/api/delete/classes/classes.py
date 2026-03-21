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
        
        # L3 cascade: clear iscountedby references on OTHER classes that point to deleted class
        iscountedby_rollback = []
        for cls_item in class_data_store:
            for day in ['1', '2', '3']:
                field = f'iscountedby{day}'
                if cls_item.get(field) == class_name:
                    iscountedby_rollback.append((cls_item, field, class_name))
                    cls_item[field] = '_NULL_'
        
        if save_class_data_to_db():
            # L4 cascade: clean student assignments
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

                    needs_update = False

                    # Remove deleted class from this student's counting list
                    if class_name in personal_counts:
                        personal_counts = [c for c in personal_counts if c != class_name]
                        needs_update = True

                    # If student belongs to the deleted class, clear ALL their counting assignments
                    # (their class no longer has any counting role)
                    if student.get('class') == class_name and personal_counts:
                        personal_counts = []
                        needs_update = True

                    if needs_update:
                        student['counts_classes'] = json.dumps(personal_counts)
                        students_modified = True
                except Exception as e:
                    print(f"Error checking student {student.get('code')} for removed class: {e}")
            
            if students_modified:
                save_students_data_to_db()

            return {"success": True, "message": f"Class '{class_name}' removed successfully."}
        else:
            # Rollback: restore deleted class and iscountedby references
            class_data_store.append(found_class)
            class_data_store.sort(key=lambda x: x['class'])
            for cls_item, field, old_value in iscountedby_rollback:
                cls_item[field] = old_value
            raise HTTPException(status_code=500, detail=f"Failed to save removal of class '{class_name}'.")
