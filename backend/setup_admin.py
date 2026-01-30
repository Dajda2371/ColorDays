import sys
import os
import sqlite3
import getpass
import argparse

# Ensure we can import from the same directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import DATABASE_FILE, ADMIN_ROLE
from utils import hash_password

def setup_admin(username="admin", password=None):
    if not password:
        password = getpass.getpass(f"Enter password for '{username}': ")
        confirm_password = getpass.getpass(f"Confirm password for '{username}': ")
        if password != confirm_password:
            print("Passwords do not match!")
            return False

    hashed_password = hash_password(password)
    
    print(f"Updating admin user '{username}' in {DATABASE_FILE}...")
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if user:
            print(f"User '{username}' exists. Updating password...")
            cursor.execute("UPDATE users SET password_hash = ?, role = ? WHERE username = ?", (hashed_password, ADMIN_ROLE, username))
        else:
            print(f"User '{username}' does not exist. Creating...")
            cursor.execute("INSERT INTO users (username, password_hash, role, profile_picture_url) VALUES (?, ?, ?, ?)", 
                           (username, hashed_password, ADMIN_ROLE, '_NULL_'))
        
        conn.commit()
        conn.close()
        print("Admin user updated successfully.")
        return True
    except Exception as e:
        print(f"Error updating database: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup admin password")
    parser.add_argument("--username", default="admin", help="Username (default: admin)")
    parser.add_argument("--password", help="Password (optional, will prompt if not provided)")
    
    args = parser.parse_args()
    
    setup_admin(args.username, args.password)
