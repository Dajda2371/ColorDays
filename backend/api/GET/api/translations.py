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


@router.get("/api/translations")
def get_translations():
    if TRANSLATIONS_FILE_PATH.is_file():
        try:
            with open(TRANSLATIONS_FILE_PATH, 'rb') as f:
                content = f.read()
            # Return raw json content
            return Response(content=content, media_type='application/json')
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"Error serving translations file: {e}")
    else:
         raise HTTPException(status_code=404, detail="Translations file not found.")
