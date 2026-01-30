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
