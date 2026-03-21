from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from config import ADMIN_ROLE
from dependencies import get_current_admin_user
from data_manager import class_data_store, data_lock, save_class_data_to_db, students_data_store, save_students_data_to_db
import json

router = APIRouter()

class UpdateCountsRequest(BaseModel):
    class_: str = Field(..., alias="class")
    countField: str
    value: str

@router.put("/api/classes/counts")
def update_classes_counts(payload: UpdateCountsRequest, admin_user: dict = Depends(get_current_admin_user)):
    class_name = payload.class_
    count_field = payload.countField
    new_value = payload.value

    valid_count_fields = ["counts1", "counts2", "counts3"]
    if count_field not in valid_count_fields:
        raise HTTPException(status_code=400, detail=f"Invalid countField. Must be one of {valid_count_fields}")

    if new_value not in ['T', 'F']:
        raise HTTPException(status_code=400, detail="Invalid value. Must be 'T' or 'F'")

    with data_lock:
        class_to_update = next((cls_item for cls_item in class_data_store if cls_item['class'] == class_name), None)

        if not class_to_update:
             raise HTTPException(status_code=404, detail=f"Class '{class_name}' not found.")
        
        old_value = class_to_update[count_field]
        class_to_update[count_field] = new_value
        
        # L3 cascade: if counting was disabled (T -> F), clear iscountedby references for that day
        day_number = count_field[-1]  # "counts1" -> "1"
        iscountedby_field = f"iscountedby{day_number}"
        
        cleared_classes = []
        if old_value == 'T' and new_value == 'F':
            for cls_item in class_data_store:
                if cls_item.get(iscountedby_field) == class_name:
                    cleared_classes.append(cls_item['class'])
                    cls_item[iscountedby_field] = '_NULL_'
        
        if save_class_data_to_db():
            # L4 cascade: clean student assignments if L3 was affected
            if cleared_classes:
                students_modified = False
                for student in students_data_store:
                    if student.get('class') != class_name:
                        continue  # Only students belonging to the class that lost its counting role
                    
                    try:
                        counts_list_str = student.get('counts_classes', '[]')
                        try:
                            personal_counts = json.loads(counts_list_str)
                            if not isinstance(personal_counts, list):
                                personal_counts = []
                        except json.JSONDecodeError:
                            personal_counts = []
                        
                        if not personal_counts:
                            continue
                        
                        new_personal_counts = []
                        needs_update = False
                        
                        for counted_class in personal_counts:
                            if counted_class in cleared_classes:
                                # Check if the student's class still counts this class on ANY other day
                                c_obj = next((c for c in class_data_store if c['class'] == counted_class), None)
                                if c_obj:
                                    still_assigned = any(
                                        c_obj.get(f'iscountedby{d}') == class_name for d in ['1', '2', '3']
                                    )
                                    if still_assigned:
                                        new_personal_counts.append(counted_class)
                                    else:
                                        needs_update = True
                                else:
                                    needs_update = True
                            else:
                                new_personal_counts.append(counted_class)
                        
                        if needs_update:
                            student['counts_classes'] = json.dumps(new_personal_counts)
                            students_modified = True
                    except Exception as e:
                        print(f"Error cleaning student {student.get('code')}: {e}")
                
                if students_modified:
                    save_students_data_to_db()
            
            return {"success": True, "message": f"Count '{count_field}' for class '{class_name}' updated to '{new_value}'."}
        else:
            # Rollback: restore counts field and iscountedby references
            class_to_update[count_field] = old_value
            for cls_item in class_data_store:
                if cls_item['class'] in cleared_classes:
                    cls_item[iscountedby_field] = class_name
            raise HTTPException(status_code=500, detail=f"Count for class '{class_name}' updated in memory, but FAILED to save to file.")
