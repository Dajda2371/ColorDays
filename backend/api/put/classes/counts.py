from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from config import ADMIN_ROLE
from dependencies import get_current_admin_user
from data_manager import class_data_store, data_lock, save_class_data_to_db

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
        
        class_to_update[count_field] = new_value
        
        if save_class_data_to_db():
            return {"success": True, "message": f"Count '{count_field}' for class '{class_name}' updated to '{new_value}'."}
        else:
            raise HTTPException(status_code=500, detail=f"Count for class '{class_name}' updated in memory, but FAILED to save to file.")
