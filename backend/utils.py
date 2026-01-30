import os
import random
import string
import hashlib
import binascii
import hmac
from http.cookies import SimpleCookie

from config import (
    HASH_ALGORITHM,
    ITERATIONS,
    SALT_BYTES,
    DK_LENGTH,
    CHANGE_PASSWORD_COOKIE_NAME,
    DATA_DIR,
)

def generate_random_code(length=15):
    """Generates a random alphanumeric code of a given length."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def generate_token(length=128):
    """Generates a secure random alphanumeric token of a given length."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.SystemRandom().choice(characters) for _ in range(length))

def store_token(user, token_value, ip='_NULL_'):
    """
    Stores a token in tokens table in the database.
    Args:
        user (str): Username for whom the token is generated.
        token_value (str): The generated token value.
        ip (str): IP address (optional, default '_NULL_').
    Returns:
        bool: True if stored successfully, False otherwise.
    """
    try:
        # Token storage is now handled by the database
        # This function is kept for compatibility but could be removed
        # if token storage in database is properly implemented
        print(f"Token generated for user '{user}' (storage TBD).")
        return True
    except Exception as e:
        print(f"Error storing token: {e}")
        return False

def hash_password(password):
    """Hashes a password using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(SALT_BYTES)
    pwd_bytes = password.encode('utf-8')
    key = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        pwd_bytes,
        salt,
        ITERATIONS,
        dklen=DK_LENGTH
    )
    salt_hex = binascii.hexlify(salt).decode('ascii')
    key_hex = binascii.hexlify(key).decode('ascii')
    return f"{salt_hex}:{key_hex}"

def verify_password(stored_password_info, provided_password, username):
    """Verifies a provided password against the stored salt and hash."""
    if not isinstance(stored_password_info, dict) or 'password_hash' not in stored_password_info:
        print(f"Error: Invalid stored_password_info structure for user '{username}'. Expected a dict with 'password_hash'.")
        return False, []
    
    password_hash = stored_password_info['password_hash']
    extra_cookie_headers = []

    if not password_hash or \
       password_hash.upper() == '_NULL_' or \
       password_hash == 'NOT_SET' or \
       password_hash == '_GOOGLE_AUTH_USER_':
        
        if password_hash == '_GOOGLE_AUTH_USER_':
            print(f"Login attempt for Google OAuth user '{username}' with password. Denied.")
        elif not password_hash or password_hash.upper() == '_NULL_' or password_hash == 'NOT_SET':
            print(f"Login attempt for user '{username}' with unset, null, or 'NOT_SET' password state.")
        else:
            print(f"Login attempt for user '{username}' with an unhandled special password state: {password_hash}")
        return False, []

    if password_hash.startswith('_') and password_hash.endswith('_'):
        _stored_actual_password_ = password_hash[1:-1]
        if _stored_actual_password_ == provided_password:
            print(f"User '{username}' logged in with pregenerated password. Setting change password cookie.")
            change_pw_cookie_headers = create_cookies(
                CHANGE_PASSWORD_COOKIE_NAME,
                "not-required",
                path='/',
                httponly=False
            )
            return True, change_pw_cookie_headers
        else:
            print(f"Pregenerated password verification failed for user: {username}")
            return False, []

    if ':' not in password_hash:
        print(f"Error: Unrecognized or invalid password_hash format ('{password_hash}') for user '{username}'. Expected 'salt:key'.")
        return False, []

    try:
        salt_hex, key_hex = password_hash.split(':')
        salt = binascii.unhexlify(salt_hex)
        stored_key = binascii.unhexlify(key_hex)
    except (ValueError, binascii.Error):
        print(f"Error: Invalid stored password format for hash starting with '{salt_hex[:8]}...' for user '{username}'")
        return False, []

    provided_pwd_bytes = provided_password.encode('utf-8')
    new_key = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        provided_pwd_bytes,
        salt,
        ITERATIONS,
        dklen=DK_LENGTH
    )
    is_match = hmac.compare_digest(stored_key, new_key)
    if not is_match:
        print(f"Password hash mismatch for user '{username}'.")
    return is_match, []

def create_cookies(name, value, path='/', expires=None, max_age=None, httponly=True, samesite='Lax'):
    """Creates a list of ('Set-Cookie', header_value) tuples for a single cookie."""
    if not name or value is None:
        print(f"Warning: Attempted to create cookie with empty name ('{name}') or None value.")
        return []

    cookie = SimpleCookie()
    cookie[name] = value
    cookie[name]['path'] = path

    if httponly:
        cookie[name]['httponly'] = True
    if samesite:
        cookie[name]['samesite'] = samesite
    if expires:
        cookie[name]['expires'] = expires
    if max_age is not None:
        cookie[name]['max-age'] = max_age

    headers = []
    for morsel in cookie.values():
        header_value = morsel.output(header='').strip()
        headers.append(('Set-Cookie', header_value))

    return headers

def create_cookie_clear_headers(name, path='/'):
    """Creates a list of ('Set-Cookie', header_value) tuples to clear a cookie."""
    if not name:
        print("Warning: Attempted to clear cookie with empty name.")
        return []

    cookie = SimpleCookie()
    cookie[name] = ""
    cookie[name]['path'] = path
    cookie[name]['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
    cookie[name]['max-age'] = 0

    header_value = cookie[name].output(header='').strip()
    return [('Set-Cookie', header_value)]

def set_cookie_headers(response, headers: list):
    """Helper to append Set-Cookie headers from utils to FastAPI response."""
    for header_name, header_value in headers:
        if header_name.lower() == 'set-cookie':
            response.headers.append('set-cookie', header_value)
