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


@router.get("/api/users", response_model=List[dict])
def list_users(admin_user: dict = Depends(get_current_admin_user)):
    user_list = []
    with data_lock:
        for username_key, user_data_val in user_password_store.items():
            password_hash = user_data_val['password_hash']
            role = user_data_val.get('role', DEFAULT_ROLE_FOR_NEW_USERS)

            status = "set"
            if password_hash is None or password_hash.upper() == '_NULL_':
                status = "not_set"
            elif password_hash == '_GOOGLE_AUTH_USER_':
                status = "google_auth_user"
            elif password_hash == 'NOT_SET':
                status = "not_set"
            elif password_hash.startswith('_') and password_hash.endswith('_') and \
                 password_hash.upper() != '_NULL_' and password_hash.upper() != '_GOOGLE_AUTH_USER_':
                status = password_hash[1:-1]

            user_list.append({
                "username": username_key,
                "password": status,
                "role": role
            })
    return user_list
