import json
from fastapi import APIRouter, Depends, HTTPException
from config import DATA_DIR, DOMAIN, PORT, ADMIN_ROLE
from dependencies import get_current_admin_user

router = APIRouter()

@router.get("/api/data/config")
def get_data_config(admin_user: dict = Depends(get_current_admin_user)):
    config_file_path = DATA_DIR / 'config.json'
    config_json = {}
    if config_file_path.is_file():
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config_json = json.load(f)
        except Exception as e:
            pass
    config_json['DOMAIN'] = DOMAIN
    config_json['PORT'] = PORT
    return config_json
