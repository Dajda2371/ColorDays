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


@router.post("/api/users/reset")
def reset_user_password(data: UserSetPasswordRequest, admin_user: dict = Depends(get_current_admin_user)):
    return set_user_password(data, admin_user)
