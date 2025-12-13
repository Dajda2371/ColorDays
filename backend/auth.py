from config import (
    SQL_COOKIE_NAME,
    GOOGLE_COOKIE_NAME,
    USERNAME_COOKIE_NAME,
    DEFAULT_ROLE_FOR_NEW_USERS
)

user_password_store = {}

def get_current_user_info(handler_instance):
    """
    Retrieves the authenticated user's key (as used in user_password_store) and their role.
    """
    cookies = handler_instance.get_cookies()
    
    username_key_in_store = None
    sql_auth_cookie = cookies.get(SQL_COOKIE_NAME)
    if sql_auth_cookie and sql_auth_cookie.value in user_password_store:
        username_key_in_store = sql_auth_cookie.value
    
    if not username_key_in_store:
        google_auth_cookie = cookies.get(GOOGLE_COOKIE_NAME)
        if google_auth_cookie and google_auth_cookie.value in user_password_store:
            username_key_in_store = google_auth_cookie.value

    if not username_key_in_store:
        username_cookie = cookies.get(USERNAME_COOKIE_NAME)
        if username_cookie and username_cookie.value in user_password_store:
            username_key_in_store = username_cookie.value

    if username_key_in_store:
        user_data = user_password_store.get(username_key_in_store)
        if user_data:
            return username_key_in_store, user_data.get('role', DEFAULT_ROLE_FOR_NEW_USERS)
    return None, None

def is_user_using_oauth(username):
    user_data = user_password_store.get(username)
    if user_data and user_data.get('password_hash') == '_GOOGLE_AUTH_USER_':
        print(f"User '{username}' is using Google OAuth. Password change not allowed.")
        return True
    return False
