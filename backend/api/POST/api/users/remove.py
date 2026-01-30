from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from config import DEFAULT_ROLE_FOR_NEW_USERS
from data_manager import user_password_store, data_lock, save_user_data_to_db, is_user_using_oauth
from dependencies import get_current_admin_user


router = APIRouter()

class UserAddRequest(BaseModel):
    username: str


class UserRemoveRequest(BaseModel):
    username: str


class UserSetPasswordRequest(BaseModel):
    username: str
    new_password: str


@router.post("/api/users/remove")
def remove_user(data: UserRemoveRequest, admin_user: dict = Depends(get_current_admin_user)):
    username = data.username
    if not username:
        raise HTTPException(status_code=400, detail="Missing username")
    if username == 'admin':
        raise HTTPException(status_code=403, detail="Cannot remove the admin user.")

    with data_lock:
        if username not in user_password_store:
             raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

        del user_password_store[username]

        if save_user_data_to_db():
            return {"success": True, "message": f"User '{username}' removed successfully."}
        else:
             raise HTTPException(status_code=500, detail=f"User '{username}' removed from memory, but FAILED to save to file.")
