from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from dependencies import get_current_admin_user
from auth import is_user_using_oauth
from data_manager import user_password_store, data_lock, save_user_data_to_db
from config import ADMIN_ROLE, TEACHER_ROLE

router = APIRouter()

class UserSetPasswordRequest(BaseModel):
    username: str
    new_password: str

class UserSetRoleRequest(BaseModel):
    username: str
    role: str

@router.put("/api/users")
def set_user_password(payload: UserSetPasswordRequest, admin_user: dict = Depends(get_current_admin_user)):
    username = payload.username
    new_password = payload.new_password

    if is_user_using_oauth(username):
        raise HTTPException(status_code=403, detail="Password change not allowed for Google OAuth users.")

    if not username or not new_password:
        raise HTTPException(status_code=400, detail="Missing username or new_password")

    if username == "admin" and admin_user["username"] != "admin":
        raise HTTPException(status_code=403, detail="Only the main admin user can reset their own password.")

    with data_lock:
        if username not in user_password_store:
             raise HTTPException(status_code=404, detail=f"User '{username}' not found.")
        
        hashed = f"_{new_password}_"
        user_password_store[username]['password_hash'] = hashed
        
        if save_user_data_to_db():
            return {"success": True, "message": f"Password for user '{username}' set/reset successfully."}
        else:
            raise HTTPException(status_code=500, detail="Failed to save data.")

@router.put("/api/users/role")
def set_user_role(payload: UserSetRoleRequest, admin_user: dict = Depends(get_current_admin_user)):
    username = payload.username
    new_role = payload.role

    if not username or not new_role:
        raise HTTPException(status_code=400, detail="Missing username or role")

    if new_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        raise HTTPException(status_code=400, detail="Invalid role")

    if username == "admin":
        raise HTTPException(status_code=403, detail="Cannot change role of the main admin user.")

    if username == admin_user["username"]:
        raise HTTPException(status_code=403, detail="You cannot change your own role.")

    with data_lock:
        if username not in user_password_store:
             raise HTTPException(status_code=404, detail=f"User '{username}' not found.")
        
        user_password_store[username]['role'] = new_role
        
        if save_user_data_to_db():
            return {"success": True, "message": f"Role for user '{username}' updated successfully."}
        else:
            raise HTTPException(status_code=500, detail="Failed to save data.")
