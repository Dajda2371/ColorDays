from fastapi import APIRouter, Depends
from config import DEFAULT_ROLE_FOR_NEW_USERS
from data_manager import user_password_store, data_lock
from dependencies import get_current_admin_user

router = APIRouter()

@router.get("/api/users")
def get_users(admin_user: dict = Depends(get_current_admin_user)):
    user_list = []
    with data_lock:
        for username_key, user_data_val in user_password_store.items():
            password_hash = user_data_val['password_hash']
            role = user_data_val.get('role', DEFAULT_ROLE_FOR_NEW_USERS)

            # Determine password status for frontend
            status = "set"  # Default
            if password_hash is None or password_hash.upper() == '_NULL_':
                status = "not_set"
            elif password_hash == '_GOOGLE_AUTH_USER_':
                status = "google_auth_user"
            elif password_hash == 'NOT_SET':
                status = "not_set"
            # Check for pre-generated passwords like _password_
            elif password_hash.startswith('_') and password_hash.endswith('_') and \
                 password_hash.upper() != '_NULL_' and password_hash.upper() != '_GOOGLE_AUTH_USER_':
                status = password_hash[1:-1]  # Extract the pre-generated password

            user_list.append({
                "username": username_key,
                "password": status,  # 'password' field name for frontend compatibility
                "role": role
            })
    return user_list
