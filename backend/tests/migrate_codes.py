import sqlite3
import os

db_path = "/Users/david/code/ColorDays/backend/data/2026.db"

def migrate():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT code FROM students")
    codes = cursor.fetchall()
    
    updated_codes = []
    seen = set()
    
    for (old_code,) in codes:
        new_code = old_code[:5]
        # In case of collisions (unlikely but possible with 5 chars)
        original_new_code = new_code
        counter = 1
        while new_code in seen:
            # Shift or change last char? Let's just append or something. 
            # But we want exactly 5 chars.
            # Maybe just pick another random if duplicate?
            import random
            import string
            characters = string.ascii_letters + string.digits
            new_code = ''.join(random.choice(characters) for i in range(5))
        
        seen.add(new_code)
        updated_codes.append((new_code, old_code))
    
    for new_code, old_code in updated_codes:
        cursor.execute("UPDATE students SET code = ? WHERE code = ?", (new_code, old_code))
    
    conn.commit()
    conn.close()
    print(f"Migrated {len(updated_codes)} student codes to 5 characters.")

if __name__ == "__main__":
    migrate()
