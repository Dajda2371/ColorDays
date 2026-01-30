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


@router.post("/api/users/set")
def set_user_password(data: UserSetPasswordRequest, admin_user: dict = Depends(get_current_admin_user)):
    username = data.username
    new_password = data.new_password

    with data_lock:
        if is_user_using_oauth(username):
            raise HTTPException(status_code=403, detail="Password change not allowed for Google OAuth users.")

        user_data = user_password_store.get(username)
        if not user_data:
             raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

        hashed = f"_{new_password}_"
        user_password_store[username]['password_hash'] = hashed

        if save_user_data_to_db():
            return {"success": True, "message": f"Password for user '{username}' set/reset successfully."}
        else:
             raise HTTPException(status_code=500, detail=f"Password set/reset in memory for '{username}', but FAILED to save to file.")
