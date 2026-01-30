from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import List, Union
from dependencies import get_current_admin_user
from data_manager import save_main_config_to_json

router = APIRouter()

class ConfigSaveRequest(BaseModel):
    oauth_eneabled: str
    allowed_oauth_domains: List[str]

@router.post("/api/data/save/config")
def save_data_config(payload: ConfigSaveRequest, admin_user: dict = Depends(get_current_admin_user)):
    if payload.oauth_eneabled not in ["true", "false"]:
        raise HTTPException(status_code=400, detail="'oauth_eneabled' must be 'true' or 'false'.")

    # Reconstruct dict for save function
    data_to_save = payload.dict() 
    
    if save_main_config_to_json(data_to_save):
        return {"message": "OAuth configuration saved successfully."}
    else:
        raise HTTPException(status_code=500, detail="Failed to save OAuth configuration to file.")
