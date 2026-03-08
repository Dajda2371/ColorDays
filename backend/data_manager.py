import sqlite3
import re
import json
import datetime
import traceback
import collections
import threading
from config import (
    DATA_DIR,
    CURRENT_YEAR_DIR,
    DATABASE_FILE,
    YEAR_DATABASE_FILE,
    SUPPORTED_CLASSES,
    DEFAULT_ROLE_FOR_NEW_USERS
)
from utils import generate_random_code, hash_password

data_lock = threading.RLock()
class_data_store = []
students_data_store = []
user_password_store = {}
server_config = {}

def ensure_year_data_directory_exists():
    """Creates the /data/<current year> directory if it doesn't exist."""
    print(f"Ensuring year data directory exists: {CURRENT_YEAR_DIR}")
    CURRENT_YEAR_DIR.mkdir(parents=True, exist_ok=True)
    print("Year data directory check complete.")

def is_student_allowed(student_code_from_cookie, requested_class_name, requested_day_identifier):
    """
    Checks if a student is allowed to access/modify data for a specific class and day.
    """
    global students_data_store, class_data_store

    current_student_data = None
    for s_data in students_data_store:
        if s_data.get('code') == student_code_from_cookie:
            current_student_data = s_data
            break
    
    if not current_student_data:
        print(f"Security Check Failed: Student code '{student_code_from_cookie}' not found in students_data_store.")
        return False

    student_main_class = current_student_data.get('class')
    if not student_main_class:
        print(f"Security Check Failed: Student '{student_code_from_cookie}' has no main class assigned.")
        return False

    student_personal_counting_list_str = current_student_data.get('counts_classes', '[]')
    student_personal_counting_set = set()
    if student_personal_counting_list_str.startswith('[') and student_personal_counting_list_str.endswith(']'):
        content = student_personal_counting_list_str[1:-1]
        if content.strip():
            student_personal_counting_set = {c.strip() for c in content.split(',') if c.strip()}

    day_map_to_iscountedby_flag = {"monday": "iscountedby1", "tuesday": "iscountedby2", "wednesday": "iscountedby3"}
    iscountedby_flag_for_day = day_map_to_iscountedby_flag.get(requested_day_identifier.lower())

    if not iscountedby_flag_for_day:
        print(f"Security Check Failed: Invalid day identifier '{requested_day_identifier}' for student '{student_code_from_cookie}'.")
        return False

    if not any(cls_data.get(iscountedby_flag_for_day) == student_main_class for cls_data in class_data_store):
        print(f"Security Check Failed: Student '{student_code_from_cookie}' (main class: {student_main_class}) is not assigned to supervise counting on day '{requested_day_identifier}'.")
        return False

    if requested_class_name not in student_personal_counting_set:
        print(f"Security Check Failed: Student '{student_code_from_cookie}' is not assigned to count class '{requested_class_name}'. Allowed: {student_personal_counting_set}")
        return False

    print(f"Security Check Passed: Student '{student_code_from_cookie}' ALLOWED for class '{requested_class_name}' on day '{requested_day_identifier}'.")
    return True





def get_db_connection(db_file):
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables(db_file, schema_file):
    """Creates tables in the database using the provided schema."""
    with get_db_connection(db_file) as conn:
        with open(schema_file, 'r') as f:
            conn.executescript(f.read())

def migrate_logins_to_db():
    """Migrates user data from logins.sql to the database."""
    print("Migrating logins...")
    with get_db_connection(DATABASE_FILE) as conn:
        conn.execute("DELETE FROM users")
        with open(DATA_DIR / 'logins.sql', 'r') as f:
            for line in f:
                if line.strip() and line.upper().startswith("INSERT INTO USERS"):
                    match = re.match(r"INSERT INTO users\s*\((.*?)\)\s*VALUES\s*\((.*?)\);", line, re.IGNORECASE)
                    if match:
                        columns_str, values_str = match.groups()
                        columns = [col.strip().lower() for col in columns_str.split(',')]
                        value_parts = []
                        temp_val = ""
                        in_string_literal = False
                        for char_idx, char_val in enumerate(values_str):
                            if char_val == "'":
                                if in_string_literal and char_idx + 1 < len(values_str) and values_str[char_idx+1] == "'":
                                    temp_val += "'"
                                else:
                                    in_string_literal = not in_string_literal
                                    if not in_string_literal:
                                        value_parts.append(temp_val)
                                        temp_val = ""
                            elif in_string_literal:
                                temp_val += char_val
                        
                        if len(columns) == len(value_parts):
                            parsed_data = dict(zip(columns, value_parts))
                            conn.execute(
                                "INSERT INTO users (username, password_hash, role, profile_picture_url) VALUES (?, ?, ?, ?)",
                                (
                                    parsed_data.get('username'),
                                    parsed_data.get('password_hash'),
                                    parsed_data.get('role', DEFAULT_ROLE_FOR_NEW_USERS),
                                    parsed_data.get('profile_picture_url', '_NULL_')
                                )
                            )
        conn.commit()
    print("Logins migrated.")

def migrate_tokens_to_db():
    """Migrates token data from tokens.sql to the database."""
    print("Migrating tokens...")
    with get_db_connection(DATABASE_FILE) as conn:
        conn.execute("DELETE FROM tokens")
        with open(DATA_DIR / 'tokens.sql', 'r') as f:
            for line in f:
                if line.strip() and line.upper().startswith("INSERT INTO TOKENS"):
                    match = re.match(r"INSERT INTO tokens\s*\((.*?)\)\s*VALUES\s*\((.*?)\);", line, re.IGNORECASE)
                    if match:
                        columns_str, values_str = match.groups()
                        columns = [col.strip().lower() for col in columns_str.split(',')]
                        value_parts = []
                        temp_val = ""
                        in_string_literal = False
                        for char_idx, char_val in enumerate(values_str):
                            if char_val == "'":
                                if in_string_literal and char_idx + 1 < len(values_str) and values_str[char_idx+1] == "'":
                                    temp_val += "'"
                                else:
                                    in_string_literal = not in_string_literal
                                    if not in_string_literal:
                                        value_parts.append(temp_val)
                                        temp_val = ""
                            elif in_string_literal:
                                temp_val += char_val
                        
                        if len(columns) == len(value_parts):
                            parsed_data = dict(zip(columns, value_parts))
                            conn.execute(
                                "INSERT INTO tokens (token, email) VALUES (?, ?)",
                                (
                                    parsed_data.get('token'),
                                    parsed_data.get('email')
                                )
                            )
        conn.commit()
    print("Tokens migrated.")

def migrate_classes_to_db():
    """Migrates class data from classes.sql to the database."""
    print("Migrating classes...")
    with get_db_connection(YEAR_DATABASE_FILE) as conn:
        conn.execute("DELETE FROM classes")
        with open(DATA_DIR / '2025' / 'classes.sql', 'r') as f:
            for line in f:
                if line.strip() and line.upper().startswith("INSERT INTO CLASSES"):
                    match = re.match(r"INSERT INTO classes\s*\((.*?)\)\s*VALUES\s*\((.*?)\);", line, re.IGNORECASE)
                    if match:
                        columns_str, values_str = match.groups()
                        columns = [col.strip().lower() for col in columns_str.split(',')]
                        value_parts = []
                        temp_val = ""
                        in_string_literal = False
                        for char_idx, char_val in enumerate(values_str):
                            if char_val == "'":
                                if in_string_literal and char_idx + 1 < len(values_str) and values_str[char_idx+1] == "'":
                                    temp_val += "'"
                                else:
                                    in_string_literal = not in_string_literal
                                    if not in_string_literal:
                                        value_parts.append(temp_val)
                                        temp_val = ""
                            elif in_string_literal:
                                temp_val += char_val
                        
                        if len(columns) == len(value_parts):
                            parsed_data = dict(zip(columns, value_parts))
                            conn.execute(
                                "INSERT INTO classes (class, teacher, counts1, counts2, counts3, iscountedby1, iscountedby2, iscountedby3) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (
                                    parsed_data.get('class'),
                                    parsed_data.get('teacher'),
                                    parsed_data.get('counts1'),
                                    parsed_data.get('counts2'),
                                    parsed_data.get('counts3'),
                                    parsed_data.get('iscountedby1'),
                                    parsed_data.get('iscountedby2'),
                                    parsed_data.get('iscountedby3')
                                )
                            )
        conn.commit()
    print("Classes migrated.")

def migrate_students_to_db():
    """Migrates student data from students.sql to the database."""
    print("Migrating students...")
    with get_db_connection(YEAR_DATABASE_FILE) as conn:
        conn.execute("DELETE FROM students")
        with open(DATA_DIR / '2025' / 'students.sql', 'r') as f:
            for line in f:
                if line.strip() and line.upper().startswith("INSERT INTO STUDENTS"):
                    match = re.match(r"INSERT INTO students\s*\((.*?)\)\s*VALUES\s*\((.*?)\);", line, re.IGNORECASE)
                    if match:
                        columns_str, values_str = match.groups()
                        columns = [col.strip().lower() for col in columns_str.split(',')]
                        value_parts = []
                        temp_val = ""
                        in_string_literal = False
                        for char_idx, char_val in enumerate(values_str):
                            if char_val == "'":
                                if in_string_literal and char_idx + 1 < len(values_str) and values_str[char_idx+1] == "'":
                                    temp_val += "'"
                                else:
                                    in_string_literal = not in_string_literal
                                    if not in_string_literal:
                                        value_parts.append(temp_val)
                                        temp_val = ""
                            elif in_string_literal:
                                temp_val += char_val

                        if len(columns) == len(value_parts):
                            parsed_data = dict(zip(columns, value_parts))
                            conn.execute(
                                "INSERT INTO students (code, class, note, counts_classes) VALUES (?, ?, ?, ?)",
                                (
                                    parsed_data.get('code'),
                                    parsed_data.get('class'),
                                    parsed_data.get('note'),
                                    parsed_data.get('counts_classes')
                                )
                            )
        conn.commit()
    print("Students migrated.")

def migrate_counts_to_db():
    """Migrates count data from tables-*.sql files to separate day tables in the database."""
    print("Migrating counts...")
    day_files = {
        'monday': CURRENT_YEAR_DIR / 'tables-monday.sql',
        'tuesday': CURRENT_YEAR_DIR / 'tables-tuesday.sql',
        'wednesday': CURRENT_YEAR_DIR / 'tables-wednesday.sql'
    }

    with get_db_connection(YEAR_DATABASE_FILE) as conn:
        # Clear all day tables
        conn.execute("DELETE FROM counts_monday")
        conn.execute("DELETE FROM counts_tuesday")
        conn.execute("DELETE FROM counts_wednesday")

        for day_name, file_path in day_files.items():
            table_name = f"counts_{day_name}"

            if not file_path.exists():
                print(f"Warning: {file_path} not found, skipping...")
                continue

            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip() and line.upper().startswith("INSERT INTO COUNTS"):
                        # Parse: INSERT INTO counts (class_name, type, points, count) VALUES ('1.A', 'student', 0, 1);
                        match = re.match(r"INSERT INTO counts\s*\((.*?)\)\s*VALUES\s*\((.*?)\);", line, re.IGNORECASE)
                        if match:
                            columns_str, values_str = match.groups()
                            columns = [col.strip().lower() for col in columns_str.split(',')]

                            # Parse values more carefully to handle strings and numbers
                            value_parts = []
                            temp_val = ""
                            in_string_literal = False
                            for char_idx, char_val in enumerate(values_str):
                                if char_val == "'":
                                    if in_string_literal and char_idx + 1 < len(values_str) and values_str[char_idx+1] == "'":
                                        temp_val += "'"
                                    else:
                                        in_string_literal = not in_string_literal
                                        if not in_string_literal:
                                            value_parts.append(temp_val)
                                            temp_val = ""
                                elif char_val == ',' and not in_string_literal:
                                    if temp_val.strip():
                                        value_parts.append(temp_val.strip())
                                        temp_val = ""
                                elif in_string_literal or char_val not in [' ', ',']:
                                    temp_val += char_val

                            # Don't forget the last value
                            if temp_val.strip():
                                value_parts.append(temp_val.strip())

                            if len(value_parts) >= 4:  # class_name, type, points, count
                                conn.execute(
                                    f"INSERT INTO {table_name} (class_name, type, points, count) VALUES (?, ?, ?, ?)",
                                    (
                                        value_parts[0],  # class_name
                                        value_parts[1],  # type
                                        int(value_parts[2]),  # points
                                        int(value_parts[3]),  # count
                                    )
                                )
        conn.commit()
    print("Counts migrated.")

def load_user_data_from_db():
    """Loads user data from the database into the in-memory user_password_store."""
    global user_password_store
    print("Loading user data from database...")
    with get_db_connection(DATABASE_FILE) as conn:
        rows = conn.execute("SELECT * FROM users").fetchall()
        for row in rows:
            user_password_store[row['username']] = {
                'password_hash': row['password_hash'],
                'profile_picture_url': row['profile_picture_url'],
                'role': row['role']
            }
    print("User data loaded.")
    return user_password_store

def save_user_data_to_db():
    """Saves the current user_password_store back to the database."""
    global user_password_store
    print("Saving user data to database...")
    try:
        with get_db_connection(DATABASE_FILE) as conn:
            conn.execute("DELETE FROM users")
            for username, user_data in user_password_store.items():
                conn.execute(
                    "INSERT INTO users (username, password_hash, role, profile_picture_url) VALUES (?, ?, ?, ?)",
                    (
                        username,
                        user_data['password_hash'],
                        user_data.get('role', DEFAULT_ROLE_FOR_NEW_USERS),
                        user_data.get('profile_picture_url', '_NULL_')
                    )
                )
            conn.commit()
        print("User data saved.")
        return True
    except Exception as e:
        print(f"Error saving user data: {e}")
        return False

def load_class_data_from_db():
    """Loads data from the database into the in-memory class_data_store."""
    global class_data_store, SUPPORTED_CLASSES
    print("Loading class data from database...")
    with get_db_connection(YEAR_DATABASE_FILE) as conn:
        rows = conn.execute("SELECT * FROM classes").fetchall()
        for row in rows:
            class_data_store.append(dict(row))
        SUPPORTED_CLASSES = sorted([cls['class'] for cls in class_data_store])
    print("Class data loaded.")

def save_class_data_to_db():
    """Saves the current in-memory class_data_store back to the database."""
    global class_data_store
    print("Saving class data to database...")
    try:
        with get_db_connection(YEAR_DATABASE_FILE) as conn:
            conn.execute("DELETE FROM classes")
            for class_item in class_data_store:
                conn.execute(
                    "INSERT INTO classes (class, teacher, counts1, counts2, counts3, iscountedby1, iscountedby2, iscountedby3, state1, state2, state3) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        class_item['class'],
                        class_item['teacher'],
                        class_item['counts1'],
                        class_item['counts2'],
                        class_item['counts3'],
                        class_item['iscountedby1'],
                        class_item['iscountedby2'],
                        class_item['iscountedby3'],
                        class_item.get('state1', ''),
                        class_item.get('state2', ''),
                        class_item.get('state3', '')
                    )
                )
            conn.commit()
        print("Class data saved.")
        return True
    except Exception as e:
        print(f"Error saving class data: {e}")
        return False

def load_students_data_from_db():
    """Loads data from the database into the in-memory students_data_store."""
    global students_data_store
    print("Loading student data from database...")
    with get_db_connection(YEAR_DATABASE_FILE) as conn:
        rows = conn.execute("SELECT * FROM students").fetchall()
        for row in rows:
            students_data_store.append(dict(row))
    print("Student data loaded.")

def save_students_data_to_db():
    """Saves the current in-memory students_data_store back to the database."""
    global students_data_store
    print("Saving student data to database...")
    try:
        with get_db_connection(YEAR_DATABASE_FILE) as conn:
            conn.execute("DELETE FROM students")
            for student_item in students_data_store:
                conn.execute(
                    "INSERT INTO students (code, class, note, counts_classes) VALUES (?, ?, ?, ?)",
                    (
                        student_item['code'],
                        student_item['class'],
                        student_item['note'],
                        student_item['counts_classes']
                    )
                )
            conn.commit()
        print("Student data saved.")
        return True
    except Exception as e:
        print(f"Error saving student data: {e}")
        return False

def load_counts_from_db(day):
    """Loads data from the database for a specific day."""
    print(f"Loading counts for {day} from database...")
    table_name = f"counts_{day.lower()}"
    with get_db_connection(YEAR_DATABASE_FILE) as conn:
        rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
        temp_data = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
        for row in rows:
            temp_data[row['class_name']][row['type']][row['points']] = row['count']
    print(f"Counts for {day} loaded.")
    return temp_data

def save_counts_to_db(day, day_data_to_save):
    """Saves the provided day-specific count data to the database."""
    print(f"Saving counts for {day} to database...")
    table_name = f"counts_{day.lower()}"
    try:
        with get_db_connection(YEAR_DATABASE_FILE) as conn:
            conn.execute(f"DELETE FROM {table_name}")
            for class_name, class_data in day_data_to_save.items():
                for type_val, type_data in class_data.items():
                    for points_val, count_val in type_data.items():
                        if count_val > 0:
                            conn.execute(
                                f"INSERT INTO {table_name} (class_name, type, points, count) VALUES (?, ?, ?, ?)",
                                (class_name, type_val, points_val, count_val)
                            )
            conn.commit()
        print(f"Counts for {day} saved.")
        return True
    except Exception as e:
        print(f"Error saving counts for {day}: {e}")
        return False

def load_main_config_from_json():
    """Loads configuration from config.json into the in-memory server_config."""
    global server_config
    config_file_path = DATA_DIR / 'config.json'
    print(f"Attempting to load server configuration from: {config_file_path}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp_config = {}
    if config_file_path.is_file():
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                temp_config = json.load(f)
            print(f"Server configuration loaded from {config_file_path}.")
        except json.JSONDecodeError:
            print(f"!!! ERROR: Invalid JSON format in {config_file_path}. Server configuration might be incomplete or default.")
        except Exception as e:
            print(f"!!! ERROR reading {config_file_path}: {e}. Server configuration might be incomplete or default.")
    else:
        print(f"Warning: {config_file_path} not found. Using default server configuration.")

    server_config.clear()
    server_config.update(temp_config)
    print("Server configuration loading complete.")

def save_main_config_to_json(config_data):
    """Saves the main configuration dictionary to config.json."""
    config_file_path = DATA_DIR / 'config.json'
    print(f"Attempting to save server configuration to: {config_file_path}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(config_file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        print(f"Server configuration saved to {config_file_path}.")
        return True
    except Exception as e:
        print(f"!!! ERROR saving {config_file_path}: {e}")
        return False
def is_user_using_oauth(username: str) -> bool:
    user_data = user_password_store.get(username)
    if user_data and user_data.get('password_hash') == '_GOOGLE_AUTH_USER_':
        return True
    return False
