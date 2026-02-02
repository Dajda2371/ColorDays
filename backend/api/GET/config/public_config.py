from fastapi import APIRouter
from data_manager import server_config

router = APIRouter()

@router.get("/api/config/public")
def get_public_config():
    return {"smart_sorting": server_config.get("smart_sorting", "false")}
