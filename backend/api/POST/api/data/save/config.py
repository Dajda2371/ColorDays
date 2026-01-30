from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from typing import List, Dict, Any
from config import DATA_DIR, DOMAIN, PORT, ADMIN_ROLE, TRANSLATIONS_FILE_PATH, LANGUAGE_COOKIE_NAME
from data_manager import save_main_config_to_json
from dependencies import get_current_admin_user
from utils import create_cookies
import json


router = APIRouter()

class ConfigSaveRequest(BaseModel):
    oauth_eneabled: str
    allowed_oauth_domains: List[str]

    class Config:
        extra = "allow"


class LanguageSetRequest(BaseModel):
    language: str


@router.post("/api/data/save/config")
def save_config(request: Request, data: Dict[str, Any], admin_user: dict = Depends(get_current_admin_user)):
    # Using Dict[str, Any] to capture all fields
    oauth_eneabled = data.get('oauth_eneabled')
    allowed_domains = data.get('allowed_oauth_domains')

    if oauth_eneabled is None or not isinstance(allowed_domains, list):
         raise HTTPException(status_code=400, detail="Invalid payload. 'oauth_eneabled' (string) and 'allowed_oauth_domains' (list) are required.")

    if oauth_eneabled not in ["true", "false"]:
         raise HTTPException(status_code=400, detail="'oauth_eneabled' must be the string 'true' or 'false'.")

    if save_main_config_to_json(data):
        return {"message": "OAuth configuration saved successfully."}
    else:
         raise HTTPException(status_code=500, detail="Failed to save OAuth configuration to file.")
