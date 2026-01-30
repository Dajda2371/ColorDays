from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List
from config import ADMIN_ROLE, TEACHER_ROLE, DATA_DIR
from dependencies import get_current_user_info
from data_manager import class_data_store, data_lock, save_class_data_to_db
import json

router = APIRouter()

class UpdateIsCountedByRequest(BaseModel):
    class_: str = Field(..., alias="class")
    dayIdentifier: str
    value: str

class BatchUpdateIsCountedByRequest(BaseModel):
    updates: List[UpdateIsCountedByRequest]

@router.post("/api/classes/update_iscountedby_batch")
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
        for update in updates:
            class_name_to_update = update.class_
            day_identifier = update.dayIdentifier
            new_value = update.value

            if day_identifier not in ['1', '2', '3']:
                continue # Or raise error, but batch usually tries to continue or validate all first.

            if not allow_self_count and new_value == class_name_to_update:
                # Skip invalid update or error? 
                # For batch operations from trusted UI logic, we might just skip or error.
                # Given strictness, let's skip but maybe log? Or just let it fail silently for that item?
                # Ideally, the UI shouldn't send it.
                continue

            class_found = next((c for c in class_data_store if c['class'] == class_name_to_update), None)
            
            if class_found:
                field_to_update = f"iscountedby{day_identifier}"
                class_found[field_to_update] = new_value
                applied_count += 1
        
        if applied_count > 0:
            if save_class_data_to_db():
                return {"success": True, "message": f"Successfully processed {applied_count} updates."}
            else:
                 raise HTTPException(status_code=500, detail=f"Updates applied in memory but FAILED to save to file.")
        else:
            return {"success": True, "message": "No valid updates were applied."}
