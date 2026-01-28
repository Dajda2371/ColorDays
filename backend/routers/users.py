from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from config import DEFAULT_ROLE_FOR_NEW_USERS
from data_manager import user_password_store, data_lock, save_user_data_to_db
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

@router.post("/api/users/set")
def set_user_password(data: UserSetPasswordRequest, admin_user: dict = Depends(get_current_admin_user)):
    username = data.username
    new_password = data.new_password

    with data_lock:
        user_data = user_password_store.get(username)
        if user_data and user_data.get('password_hash') == '_GOOGLE_AUTH_USER_':
            raise HTTPException(status_code=403, detail="Password change not allowed for Google OAuth users.")

        if not user_data:
             raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

        hashed = f"_{new_password}_"
        user_password_store[username]['password_hash'] = hashed

        if save_user_data_to_db():
            return {"success": True, "message": f"Password for user '{username}' set/reset successfully."}
        else:
             raise HTTPException(status_code=500, detail=f"Password set/reset in memory for '{username}', but FAILED to save to file.")

@router.post("/api/users/reset")
def reset_user_password(data: UserSetPasswordRequest, admin_user: dict = Depends(get_current_admin_user)):
    return set_user_password(data, admin_user)
