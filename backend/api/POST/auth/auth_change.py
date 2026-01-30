from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel
from config import CHANGE_PASSWORD_COOKIE_NAME
from dependencies import get_current_user_info
from data_manager import user_password_store, data_lock, save_user_data_to_db
from utils import verify_password, hash_password

router = APIRouter()

class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str

@router.post("/api/auth/change")
def change_password(request: Request, response: Response, payload: ChangePasswordRequest, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info
    
    # Payload fields
    # username in payload seems to be for verification/lookup, but RBAC is based on logged in user
    username_for_messages = payload.username
    old_password = payload.old_password
    new_password = payload.new_password

    if not user_key:
         raise HTTPException(status_code=401, detail="Authentication required")

    user_key_for_rbac = user_key 

    with data_lock:
        stored_user_data = user_password_store.get(user_key_for_rbac)

        if not stored_user_data:
            raise HTTPException(status_code=404, detail=f"User '{username_for_messages}' not found.")
            
        is_old_valid, _ = verify_password(stored_user_data, old_password, user_key_for_rbac)
        if not is_old_valid:
            raise HTTPException(status_code=401, detail="Old password verification failed.")

        try:
            hashed_pw = hash_password(new_password)
            user_password_store[user_key_for_rbac]['password_hash'] = hashed_pw
            if save_user_data_to_db():
                 # Success
                 pass
            else:
                 raise HTTPException(status_code=500, detail="Failed to save data to file.")
        except Exception as e:
            raise HTTPException(status_code=500, detail="Server error during password hashing.")
            
    if request.cookies.get(CHANGE_PASSWORD_COOKIE_NAME):
        response.delete_cookie(key=CHANGE_PASSWORD_COOKIE_NAME, path='/')
        
    return {"success": True, "message": f"Password for user '{username_for_messages}' changed successfully."}
