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


@router.post("/api/users")
def add_user(data: UserAddRequest, admin_user: dict = Depends(get_current_admin_user)):
    username = data.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username required")

    with data_lock:
        if username in user_password_store:
             raise HTTPException(status_code=400, detail="User already exists")

        user_password_store[username] = {
            'password_hash': 'NOT_SET',
            'profile_picture_url': '_NULL_',
            'role': DEFAULT_ROLE_FOR_NEW_USERS
        }

        if save_user_data_to_db():
            return {"message": "User added"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save user data")
