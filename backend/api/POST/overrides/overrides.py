from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from config import ADMIN_ROLE
from dependencies import get_current_user_info
from data_manager import overrides_store, data_lock, save_overrides_to_db
from typing import Dict, Any

router = APIRouter()

class OverridesUpdate(BaseModel):
    overrides: Dict[str, Dict[str, Any]]

@router.post("/api/overrides")
def set_overrides(update: OverridesUpdate, request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info
    
    if user_role != ADMIN_ROLE:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
        
    with data_lock:
        overrides_store.clear()
        overrides_store.update(update.overrides)
        if not save_overrides_to_db():
            raise HTTPException(status_code=500, detail="Failed to save overrides")
            
    return {"message": "Overrides saved successfully"}
