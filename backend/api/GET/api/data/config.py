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
