from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from config import DEFAULT_ROLE_FOR_NEW_USERS
from dependencies import get_current_admin_user
from data_manager import user_password_store, save_user_data_to_db

router = APIRouter()

class UserAddRequest(BaseModel):
    username: str

@router.post("/api/users")
def add_user(payload: UserAddRequest, admin_user: dict = Depends(get_current_admin_user)):
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username required")

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
