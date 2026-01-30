import json
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from config import ADMIN_ROLE, TEACHER_ROLE, DATA_DIR
from dependencies import get_current_user_info
from data_manager import class_data_store, data_lock, save_class_data_to_db

router = APIRouter()

class UpdateIsCountedByRequest(BaseModel):
    class_: str = Field(..., alias="class")
    dayIdentifier: str
    value: str

@router.post("/api/classes/update_iscountedby")
def update_classes_iscountedby(payload: UpdateIsCountedByRequest, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info

    if not user_key:
         raise HTTPException(status_code=401, detail="Authentication required")
    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
         raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    class_name_to_update = payload.class_
    day_identifier = payload.dayIdentifier
    new_value = payload.value

    if day_identifier not in ['1', '2', '3']:
        raise HTTPException(status_code=400, detail="Invalid dayIdentifier. Must be '1', '2', or '3'.")

    field_to_update = f"iscountedby{day_identifier}"

    # Server-side check for can_students_count_their_own_class
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

    if not allow_self_count and new_value == class_name_to_update:
        raise HTTPException(status_code=400, detail=f"Configuration prevents class '{class_name_to_update}' from counting itself.")

    with data_lock:
        class_found = next((c for c in class_data_store if c['class'] == class_name_to_update), None)

        if not class_found:
            raise HTTPException(status_code=404, detail=f"Class '{class_name_to_update}' not found.")
        
        class_found[field_to_update] = new_value
        
        if save_class_data_to_db():
            return {"success": True, "message": f"Assignment for class '{class_name_to_update}' on day {day_identifier} updated to '{new_value}' and saved."}
        else:
             raise HTTPException(status_code=500, detail=f"Assignment updated in memory, but FAILED to save to file.")
