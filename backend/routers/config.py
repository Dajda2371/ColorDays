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

@router.get("/api/data/config")
def get_config(admin_user: dict = Depends(get_current_admin_user)):
    config_file_path = DATA_DIR / 'config.json'
    config_json = {}
    if config_file_path.is_file():
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config_json = json.load(f)
        except Exception:
            pass
    config_json['DOMAIN'] = DOMAIN
    config_json['PORT'] = PORT
    return config_json

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

@router.post("/api/language/set")
def set_language(data: LanguageSetRequest, response: Response):
    language_code = data.language
    if language_code not in ['cs', 'en']:
         raise HTTPException(status_code=400, detail="Invalid language code. Must be 'cs' or 'en'.")

    max_age_1_year = 365 * 24 * 60 * 60
    # Use FastAPI set_cookie
    response.set_cookie(
        key=LANGUAGE_COOKIE_NAME,
        value=language_code,
        path='/',
        max_age=max_age_1_year,
        httponly=False
    )

    return {"success": True, "message": f"Language set to {language_code}"}
