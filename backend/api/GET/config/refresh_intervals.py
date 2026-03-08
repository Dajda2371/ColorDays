from fastapi import APIRouter
from config import REFRESH_INTERVALS

router = APIRouter()

@router.get("/api/config/refresh_intervals")
def get_refresh_intervals():
    return REFRESH_INTERVALS
