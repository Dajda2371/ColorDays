from fastapi import APIRouter, Depends, HTTPException, Request
from config import ADMIN_ROLE, TEACHER_ROLE
from dependencies import get_current_user_info
from data_manager import overrides_store, data_lock

router = APIRouter()

@router.get("/api/overrides")
def get_overrides(request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info
    
    # Must be admin or teacher, but prompt says "only for the admin account"
    # Wait, the prompt specified frontend page only for admin. So endpoint should be only for admin.
    if user_role != ADMIN_ROLE:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
        
    with data_lock:
        return overrides_store
