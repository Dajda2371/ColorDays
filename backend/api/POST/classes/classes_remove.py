from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from config import ADMIN_ROLE
from dependencies import get_current_admin_user
from data_manager import class_data_store, data_lock, save_class_data_to_db

router = APIRouter()

class ClassRemoveRequest(BaseModel):
    class_: str = Field(..., alias="class")

@router.post("/api/classes/remove")
def remove_class(payload: ClassRemoveRequest, admin_user: dict = Depends(get_current_admin_user)):
    class_name = payload.class_
    
    with data_lock:
        found_class = next((c for c in class_data_store if c['class'] == class_name), None)
        if not found_class:
             raise HTTPException(status_code=404, detail=f"Class '{class_name}' not found.")
        
        class_data_store.remove(found_class)
        
        if save_class_data_to_db():
            return {"success": True, "message": f"Class '{class_name}' removed successfully."}
        else:
            class_data_store.append(found_class)
            class_data_store.sort(key=lambda x: x['class'])
            raise HTTPException(status_code=500, detail=f"Failed to save removal of class '{class_name}'.")
