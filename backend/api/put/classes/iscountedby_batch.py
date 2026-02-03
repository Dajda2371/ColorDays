from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List
from config import ADMIN_ROLE, TEACHER_ROLE, DATA_DIR
from dependencies import get_current_user_info
from data_manager import class_data_store, data_lock, save_class_data_to_db, students_data_store, save_students_data_to_db
import json

router = APIRouter()

class UpdateIsCountedByRequest(BaseModel):
    class_: str = Field(..., alias="class")
    dayIdentifier: str
    value: str

class BatchUpdateIsCountedByRequest(BaseModel):
    updates: List[UpdateIsCountedByRequest]

@router.put("/api/classes/iscountedby/batch")
def update_classes_iscountedby_batch(payload: BatchUpdateIsCountedByRequest, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info

    if not user_key:
         raise HTTPException(status_code=401, detail="Authentication required")
    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
         raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    updates = payload.updates
    if not updates:
        return {"success": True, "message": "No updates provided."}

    # Load config to check for self-count constraint
    allow_self_count_str = 'true'
    config_file_path = DATA_DIR / 'config.json'
    try:
        if config_file_path.is_file():
            with open(config_file_path, 'r', encoding='utf-8') as f:
                current_config_on_disk = json.load(f)
            allow_self_count_str = current_config_on_disk.get('can_students_count_their_own_class', 'true')
    except Exception:
        pass

    allow_self_count = allow_self_count_str.lower() == 'true'

    with data_lock:
        applied_count = 0
        updated_classes = set()

        for update in updates:
            class_name_to_update = update.class_
            day_identifier = update.dayIdentifier
            new_value = update.value

            if day_identifier not in ['1', '2', '3']:
                continue 

            if not allow_self_count and new_value == class_name_to_update:
                continue

            class_found = next((c for c in class_data_store if c['class'] == class_name_to_update), None)
            
            if class_found:
                field_to_update = f"iscountedby{day_identifier}"
                old_value = class_found.get(field_to_update)
                if old_value != new_value:
                    class_found[field_to_update] = new_value
                    updated_classes.add(class_name_to_update)
                    applied_count += 1
        
        if applied_count > 0:
            if not save_class_data_to_db():
                 raise HTTPException(status_code=500, detail=f"Updates applied in memory but FAILED to saves to file.")
            
            # Clean up student assignments
            students_modified = False
            if updated_classes:
                print(f"Cleaning up student assignments for classes: {updated_classes}")
                for student in students_data_store:
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

                        needs_update = False
                        new_personal_counts = []
                        student_main_class = student.get('class')

                        for counted_class_name in personal_counts:
                            # Only re-evaluate if this class was involved in the updates
                            # OR if we want to be safe, we could re-evaluate everything, but let's stick to updated ones for efficiency unless user implies otherwise.
                            # User said: "if student is asigned to count a specific class then it changes"
                            # So targeting updated_classes is correct.
                            
                            should_keep = True
                            if counted_class_name in updated_classes:
                                # Check if student's class still counts this class on ANY day
                                c_obj = next((c for c in class_data_store if c['class'] == counted_class_name), None)
                                if c_obj and student_main_class:
                                    is_assigned_any_day = False
                                    for d in ['1', '2', '3']:
                                        if c_obj.get(f'iscountedby{d}') == student_main_class:
                                            is_assigned_any_day = True
                                            break
                                    if not is_assigned_any_day:
                                        should_keep = False
                                else:
                                    # Class not found or student has no class - technically shouldn't happen but remove if so
                                    should_keep = False
                            
                            if should_keep:
                                new_personal_counts.append(counted_class_name)
                            else:
                                needs_update = True
                        
                        if needs_update:
                            print(f"Removing invalid assignments from student {student.get('code')}")
                            student['counts_classes'] = json.dumps(new_personal_counts)
                            students_modified = True

                    except Exception as e:
                        print(f"Error processing student {student.get('code')} for cleanup: {e}")
                
                if students_modified:
                    save_students_data_to_db()

            return {"success": True, "message": f"Successfully processed {applied_count} updates."}
        else:
            return {"success": True, "message": "No valid updates were applied."}
