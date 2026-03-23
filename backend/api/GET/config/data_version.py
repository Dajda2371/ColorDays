from fastapi import APIRouter
import data_manager

router = APIRouter()

@router.get("/api/data/version")
async def get_data_version():
    return {"version": data_manager.data_version}
