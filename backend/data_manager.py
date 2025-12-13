import re
import json
import datetime
import traceback
import collections
import threading
from config import (
    DATA_DIR,
    CURRENT_YEAR_DIR,
    CLASSES_SQL_FILE_PATH,
    STUDENTS_SQL_FILE_PATH,
    LOGINS_SQL_FILE_PATH,
    SQL_DAY_FILE_PATHS,
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

def update_data_file_paths():
    """Updates global file paths to point to the current year's directory."""
    global SQL_DAY_FILE_PATHS, CLASSES_SQL_FILE_PATH, STUDENTS_SQL_FILE_PATH
    for day in SQL_DAY_FILE_PATHS:
        SQL_DAY_FILE_PATHS[day] = CURRENT_YEAR_DIR / f'tables-{day}.sql'
    CLASSES_SQL_FILE_PATH = CURRENT_YEAR_DIR / 'classes.sql'
    STUDENTS_SQL_FILE_PATH = CURRENT_YEAR_DIR / 'students.sql'
    print(f"Data file paths updated to use directory: {CURRENT_YEAR_DIR}")

def get_sql_file_path_for_day(day_identifier):
    day_identifier = day_identifier.lower()
    if day_identifier not in SQL_DAY_FILE_PATHS:
        raise ValueError(f"Invalid day identifier: {day_identifier}. Must be one of {list(SQL_DAY_FILE_PATHS.keys())}")
    return SQL_DAY_FILE_PATHS[day_identifier]

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

    student_personal_counting_list_str = current_student_data.get('counts_classes_str', '[]')
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

def parse_sql_line(line):
    """Parses a single INSERT statement line for the counts table."""
    match = re.match(
        r"INSERT INTO counts \(class_name, type, points, count\) VALUES \('([^']*)', '([^']*)', (\d+), (\d+)\);",
        line.strip()
    )
    if match:
        class_name, type_val, points_str, count_str = match.groups()
        try:
            points = int(points_str)
            count = int(count_str)
            return class_name, type_val, points, count
        except ValueError:
            print(f"Warning: Could not parse numbers in counts line: {line.strip()}")
            return None
    else:
        if line.strip() and not line.strip().startswith('--') and not line.strip().upper().startswith('CREATE TABLE'):
             print(f"Warning: Could not parse counts line format: {line.strip()}")
        return None

def parse_classes_sql_line(line):
    """Parses a single INSERT statement line for the classes table."""
    match = re.match(
        r"INSERT INTO classes\s*\("
        r"\s*class\s*,\s*teacher\s*,\s*counts1\s*,\s*counts2\s*,\s*counts3\s*,"
        r"\s*iscountedby1\s*,\s*iscountedby2\s*,\s*iscountedby3\s*"
        r"\)\s*VALUES\s*\("
        r"\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([TF])'\s*,\s*'([TF])'\s*,\s*'([TF])'\s*,"
        r"\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*"
        r"\);",
        line.strip(),
        re.IGNORECASE
    )
    if match:
        class_name, teacher, counts1, counts2, counts3, iscountedby1, iscountedby2, iscountedby3 = match.groups()
        return {
            "class": class_name, "teacher": teacher,
            "counts1": counts1, "counts2": counts2, "counts3": counts3,
            "iscountedby1": iscountedby1,
            "iscountedby2": iscountedby2,
            "iscountedby3": iscountedby3
        }
    else:
        if line.strip() and not line.strip().startswith('--') and not line.strip().upper().startswith('CREATE TABLE'):
            print(f"Warning: Could not parse classes line format: {line.strip()}")
        return None

def parse_students_sql_line(line):
    """Parses a single INSERT statement line for the students table."""
    match = re.match(
        r"INSERT INTO students\s*\(\s*code\s*,\s*class\s*,\s*note\s*,\s*counts_classes\s*\)\s*VALUES\s*\(\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*\);",
        line.strip(),
        re.IGNORECASE
    )
    if match:
        code, class_name, note, counts_classes_str = match.groups()
        return {
            "code": code,
            "class": class_name,
            "note": note,
            "counts_classes_str": counts_classes_str
        }
    else:
        if line.strip() and not line.strip().startswith('--') and not line.strip().upper().startswith('CREATE TABLE'):
             print(f"Warning: Could not parse students line format: {line.strip()}")
        return None

def parse_logins_sql_line(line):
    """
    Parses a single valid INSERT line for the users table.
    """
    line = line.strip()
    if not line or line.startswith('--'):
        return None
    if not line.upper().startswith("INSERT INTO USERS"):
        return None
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
        
        if len(columns) != len(value_parts):
            print(f"Warning: Column count ({len(columns)}) doesn't match value count ({len(value_parts)}) in logins line: {line.strip()}")
            return None
    
        parsed_data = dict(zip(columns, value_parts))
        username = parsed_data.get('username')
        password_hash = parsed_data.get('password_hash')
        profile_picture_url = parsed_data.get('profile_picture_url', '_NULL_')
        role = parsed_data.get('role')

        if not role:
            print(f"Warning: 'role' not found or empty for user '{username}' in logins line: {line.strip()}. Assigning default role: '{DEFAULT_ROLE_FOR_NEW_USERS}'.")
            role = DEFAULT_ROLE_FOR_NEW_USERS

        if not username or not password_hash:
            print(f"Warning: Missing username or password_hash in parsed data from logins line: {line.strip()}")
            return None
        if not (':' in password_hash or password_hash.upper() == '_NULL_' or password_hash.upper() == 'GOOGLE_AUTH_USER' or (password_hash.startswith('_') and password_hash.endswith('_'))):
            print(f"Warning: User '{username}' has unrecognized password_hash format: '{password_hash}' in line: {line.strip()}. Will be loaded but may cause issues.")
            return None
        return username, password_hash, profile_picture_url, role
    else:
        if line.upper().startswith("INSERT INTO USERS"):
            print(f"Warning: Could not parse logins line format (regex mismatch): {line.strip()}")
        return None

def load_counts_from_file(file_path):
    """
    Loads data from a specific counts SQL file.
    """
    print(f"Attempting to load counts data from: {file_path}")
    
    temp_data = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
    file_existed_initially = file_path.exists()

    with data_lock:
        if file_existed_initially:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        parsed = parse_sql_line(line)
                        if parsed:
                            class_name, type_val, points, count = parsed
                            if 0 <= points <= 6 and type_val in ['student', 'teacher']:
                                temp_data[class_name][type_val][points] = count
                            else:
                                print(f"Warning: Invalid data in {file_path} line {line_num}: {line.strip()}")
                print(f"Loaded counts from {file_path}.")
            except Exception as e:
                print(f"!!! ERROR reading or parsing {file_path}: {e}. Data might be incomplete.")
        else:
            print(f"Warning: {file_path} not found. Will initialize with defaults.")

        made_changes_to_temp_data = False
        if not SUPPORTED_CLASSES:
            print("Warning: SUPPORTED_CLASSES list is empty. Cannot initialize defaults for counts files.")
        else:
            for class_name_supported in SUPPORTED_CLASSES:
                if class_name_supported not in temp_data:
                    print(f"Initializing default zero counts in {file_path} for missing class: {class_name_supported}")
                    made_changes_to_temp_data = True
                    for type_val_supported in ['student', 'teacher']:
                        for points_val_supported in range(7):
                            temp_data[class_name_supported][type_val_supported][points_val_supported] = 0

        if not file_existed_initially or made_changes_to_temp_data:
            print(f"Saving initial/default counts data to {file_path}...")
            if not save_counts_to_file(file_path, temp_data):
                 print(f"!!! CRITICAL: Failed to save initial/default counts data to {file_path}.")
            else:
                 print(f"Successfully saved initial/default counts to {file_path}.")

    print(f"Counts data loading/initialization complete for {file_path}.")
    return temp_data

def load_class_data_from_sql():
    """Loads data from classes.sql into the in-memory class_data_store."""
    global class_data_store, SUPPORTED_CLASSES
    print(f"Attempting to load class data from: {CLASSES_SQL_FILE_PATH}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp_class_store = []
    file_exists = CLASSES_SQL_FILE_PATH.exists()
    classes_loaded_count = 0

    if file_exists:
        try:
            with open(CLASSES_SQL_FILE_PATH, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    parsed = parse_classes_sql_line(line)
                    if parsed:
                        temp_class_store.append(parsed)
                        classes_loaded_count += 1
            print(f"Loaded {classes_loaded_count} class(es) from {CLASSES_SQL_FILE_PATH}.")
        except Exception as e:
            print(f"!!! ERROR reading or parsing {CLASSES_SQL_FILE_PATH}: {e}. Class data store might be empty or incomplete.")
            temp_class_store.clear()
    else:
        print(f"Warning: {CLASSES_SQL_FILE_PATH} not found. No classes loaded. Class management will start with an empty list.")

    with data_lock:
        class_data_store = temp_class_store
        SUPPORTED_CLASSES = sorted([cls['class'] for cls in class_data_store])
        if SUPPORTED_CLASSES:
            print(f"SUPPORTED_CLASSES populated: {SUPPORTED_CLASSES}")
        else:
            print("Warning: No classes loaded, SUPPORTED_CLASSES is empty.")

    print("Class data loading complete.")

def load_students_data_from_sql():
    """Loads data from students.sql into the in-memory students_data_store."""
    global students_data_store
    print(f"Attempting to load student data from: {STUDENTS_SQL_FILE_PATH}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp_students_store = []
    file_exists = STUDENTS_SQL_FILE_PATH.exists()
    students_loaded_count = 0
    codes_were_generated = False

    if file_exists:
        try:
            with open(STUDENTS_SQL_FILE_PATH, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    parsed = parse_students_sql_line(line)
                    if parsed:
                        if not parsed.get('code') or parsed['code'] == "''" or parsed['code'] == "":
                            parsed['code'] = generate_random_code()
                            codes_were_generated = True
                        temp_students_store.append(parsed)
                        students_loaded_count += 1
            print(f"Loaded {students_loaded_count} student configuration(s) from {STUDENTS_SQL_FILE_PATH}.")
        except Exception as e:
            print(f"!!! ERROR reading or parsing {STUDENTS_SQL_FILE_PATH}: {e}. Student data store might be empty or incomplete.")
            temp_students_store.clear()
    else:
        print(f"Warning: {STUDENTS_SQL_FILE_PATH} not found. No student configurations loaded.")

    with data_lock:
        students_data_store = temp_students_store

    if codes_were_generated:
        print("Generated new codes for some students during load. Saving student data...")
        if not save_students_data_to_sql():
            print("!!! CRITICAL: Failed to save student data to file after generating new codes.")

    print("Student data loading complete.")

def load_user_data_from_sql():
    """Loads user data from logins.sql into the in-memory user_password_store."""
    global user_password_store
    print(f"Attempting to load user data from: {LOGINS_SQL_FILE_PATH}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp_user_store = {}
    file_exists = LOGINS_SQL_FILE_PATH.exists()
    users_loaded_count = 0

    if file_exists:
        try:
            with open(LOGINS_SQL_FILE_PATH, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    parsed = parse_logins_sql_line(line)
                    if parsed:
                        username, password_hash, profile_picture_url, role = parsed
                        temp_user_store[username] = {
                            'password_hash': password_hash,
                            'profile_picture_url': profile_picture_url if profile_picture_url else '_NULL_',
                            'role': role
                        }
                        users_loaded_count += 1

            print(f"Loaded {users_loaded_count} user(s) from {LOGINS_SQL_FILE_PATH}.")

        except Exception as e:
            print(f"!!! ERROR reading or parsing {LOGINS_SQL_FILE_PATH}: {e}. User data store might be empty or incomplete.")
            temp_user_store.clear()

    else:
        print(f"Warning: {LOGINS_SQL_FILE_PATH} not found. No users loaded. Login will not work.")

    user_password_store = temp_user_store

    if users_loaded_count == 0:
        print("!!! WARNING: No user accounts loaded. Login functionality will be unavailable.")
        print(f"!!! Ensure {LOGINS_SQL_FILE_PATH} exists, is readable, and contains valid INSERT statements.")
        print(f"!!! Example INSERT: INSERT INTO users (username, password_hash) VALUES ('admin', '{hash_password('password123')}');")

    print("User data loading complete.")
    return user_password_store

def save_counts_to_file(file_path, day_data_to_save):
    """
    Saves the provided day-specific count data to the specified SQL file.
    """
    print(f"Attempting to save counts data to: {file_path}")
    with data_lock:
        try:
            sql_lines = []
            sql_lines.append(f"-- Data saved on {datetime.datetime.now().isoformat()} --")
            sql_lines.append(f"-- This file stores counts for: {file_path.name} --")
            sql_lines.append("")

            for class_name in sorted(day_data_to_save.keys()):
                for type_val in sorted(day_data_to_save[class_name].keys()):
                    for points_val in sorted(day_data_to_save[class_name][type_val].keys()):
                        count_val = day_data_to_save[class_name][type_val][points_val]
                        if count_val > 0:
                            safe_class_name = class_name.replace("'", "''")
                            insert_statement = f"INSERT INTO counts (class_name, type, points, count) VALUES ('{safe_class_name}', '{type_val}', {points_val}, {count_val});"
                            sql_lines.append(insert_statement)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(sql_lines))
                f.write("\n")
            print(f"Counts data successfully saved to {file_path}")
            return True

        except PermissionError as e:
            print(f"!!! PERMISSION ERROR writing to {file_path}: {e}")
            return False
        except IOError as e:
            print(f"!!! IO ERROR writing to {file_path}: {e}")
            return False
        except Exception as e:
            print(f"!!! UNEXPECTED ERROR during save_counts_to_file for {file_path}:")
            print(traceback.format_exc())
            return False
        
def save_class_data_to_sql():
    """Saves the current in-memory class_data_store back to classes.sql."""
    global class_data_store
    print(f"Attempting to save class data to: {CLASSES_SQL_FILE_PATH}")
    with data_lock:
        try:
            sql_lines = []
            sql_lines.append(f"-- Class data saved on {datetime.datetime.now().isoformat()} --")
            sql_lines.append("")

            for class_item in class_data_store:
                safe_class_name = class_item['class'].replace("'", "''")
                safe_teacher = class_item['teacher'].replace("'", "''")
                safe_iscountedby1 = str(class_item.get('iscountedby1', '_NULL_')).replace("'", "''")
                safe_iscountedby2 = str(class_item.get('iscountedby2', '_NULL_')).replace("'", "''")
                safe_iscountedby3 = str(class_item.get('iscountedby3', '_NULL_')).replace("'", "''")

                insert_statement = (
                    f"INSERT INTO classes (class, teacher, counts1, counts2, counts3, iscountedby1, iscountedby2, iscountedby3) VALUES "
                    f"('{safe_class_name}', '{safe_teacher}', '{class_item['counts1']}', '{class_item['counts2']}', '{class_item['counts3']}', "
                    f"'{safe_iscountedby1}', '{safe_iscountedby2}', '{safe_iscountedby3}');"
                )
                sql_lines.append(insert_statement)

            with open(CLASSES_SQL_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write("\n".join(sql_lines))
                f.write("\n")
            print(f"Class data successfully saved to {CLASSES_SQL_FILE_PATH}")
            return True
        except Exception as e:
            print(f"!!! UNEXPECTED ERROR during save_class_data_to_sql:")
            print(traceback.format_exc())
            return False

def save_students_data_to_sql():
    """Saves the current in-memory students_data_store back to students.sql."""
    global students_data_store
    print(f"Attempting to save student data to: {STUDENTS_SQL_FILE_PATH}")
    with data_lock:
        try:
            sql_lines = []
            for student_item in students_data_store:
                safe_code = student_item.get('code', generate_random_code()).replace("'", "''")
                safe_class_name = student_item['class'].replace("'", "''")
                safe_note = student_item['note'].replace("'", "''")
                counts_classes_value = student_item.get('counts_classes_str', '[]')
                insert_statement = (
                    f"INSERT INTO students (code, class, note, counts_classes) VALUES "
                    f"('{safe_code}', '{safe_class_name}', '{safe_note}', '{counts_classes_value}');"
                )
                sql_lines.append(insert_statement)

            with open(STUDENTS_SQL_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write("\n".join(sql_lines))
                f.write("\n")
            print(f"Student data successfully saved to {STUDENTS_SQL_FILE_PATH}")
            return True
        except Exception as e:
            print(f"!!! UNEXPECTED ERROR during save_students_data_to_sql:")
            print(traceback.format_exc())
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

    server_config = temp_config
    print("Server configuration loading complete.")

def save_user_data_to_sql():
    """Saves the current user_password_store back to logins.sql."""
    global user_password_store
    print(f"Attempting to save user data to: {LOGINS_SQL_FILE_PATH}")
    with data_lock:
        try:
            sql_lines = []
            sql_lines.append(f"-- User data saved on {datetime.datetime.now().isoformat()} --")
            sql_lines.append("")

            for username, user_data in sorted(user_password_store.items()):
                safe_username = username.replace("'", "''")
                password_hash = user_data['password_hash']
                profile_pic_url = user_data.get('profile_picture_url', '_NULL_')
                role = user_data.get('role', DEFAULT_ROLE_FOR_NEW_USERS)
                safe_profile_pic_url = profile_pic_url.replace("'", "''") if profile_pic_url else '_NULL_'
                safe_role = role.replace("'", "''")
                insert_statement = f"INSERT INTO users (username, password_hash, role, profile_picture_url) VALUES ('{safe_username}', '{password_hash}', '{safe_role}', '{safe_profile_pic_url}');"
                sql_lines.append(insert_statement)

            with open(LOGINS_SQL_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write("\n".join(sql_lines))
                f.write("\n")
            print(f"User data successfully saved to {LOGINS_SQL_FILE_PATH}")
            return True

        except PermissionError as e:
            print(f"!!! PERMISSION ERROR writing to {LOGINS_SQL_FILE_PATH}: {e}")
            return False
        except IOError as e:
            print(f"!!! IO ERROR writing to {LOGINS_SQL_FILE_PATH}: {e}")
            return False
        except Exception as e:
            print(f"!!! UNEXPECTED ERROR during save_user_data_to_sql:")
            print(traceback.format_exc())
            return False

def save_main_config_to_json(new_oauth_data):
    """
    Reads the existing config.json, updates OAuth specific keys,
    and writes the entire config back.
    """
    config_file_path = DATA_DIR / 'config.json'
    print(f"Attempting to update OAuth settings in: {config_file_path}")

    with data_lock:
        try:
            current_config = {}
            if config_file_path.exists():
                with open(config_file_path, 'r', encoding='utf-8') as f:
                    current_config = json.load(f)
            
            current_config.update(new_oauth_data)

            current_config['oauth_eneabled'] = new_oauth_data.get('oauth_eneabled', current_config.get('oauth_eneabled', 'false'))

            with open(config_file_path, 'w', encoding='utf-8') as f:
                json.dump(current_config, f, indent=4)
            
            print(f"OAuth settings successfully updated in {config_file_path}")
            return True
        except Exception as e:
            print(f"!!! UNEXPECTED ERROR during save_main_config_to_json:")
            print(traceback.format_exc())
            return False
