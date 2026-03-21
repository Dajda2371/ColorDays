from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from dependencies import get_current_admin_user
from data_manager import user_password_store, data_lock, save_user_data_to_db

router = APIRouter()



@router.delete("/api/users")
def remove_user(username: str, admin_user: dict = Depends(get_current_admin_user)):
    
    if not username:
        raise HTTPException(status_code=400, detail="Missing username")

    if username == 'admin':
        raise HTTPException(status_code=403, detail="Cannot remove the admin user.")

    if username == admin_user["username"]:
        raise HTTPException(status_code=403, detail="You cannot remove your own account.")

    with data_lock:
        if username not in user_password_store:
            # Case insensitive search logic
            found_user = next((k for k in user_password_store if k.lower() == username.lower()), None)
            if found_user:
                 raise HTTPException(status_code=404, detail=f"User '{username}' not found (case mismatch? Found: '{found_user}').")
            else:
                 raise HTTPException(status_code=404, detail=f"User '{username}' not found.")
        else:
            del user_password_store[username]
        
        if save_user_data_to_db():
            return {"success": True, "message": f"User '{username}' removed successfully."}
        else:
            raise HTTPException(status_code=500, detail="Failed to save data after removal.")
