from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME, DATA_DIR, SESSION_COOKIE_NAME, VALID_SESSION_VALUE
from data_manager import class_data_store, data_lock, save_class_data_to_db, load_class_data_from_db, server_config
from dependencies import get_current_admin_user, get_current_user_info, active_sessions
import json
import requests
import re
import logging

logger = logging.getLogger('ColorDaysLogger')

router = APIRouter()

class ClassAddRequest(BaseModel):
    class_: str = Field(..., alias="class")
    teacher: str
    counts1: Optional[str] = 'F'
    counts2: Optional[str] = 'F'
    counts3: Optional[str] = 'F'
    iscountedby1: Optional[str] = '_NULL_'
    iscountedby2: Optional[str] = '_NULL_'
    iscountedby3: Optional[str] = '_NULL_'

class ClassRemoveRequest(BaseModel):
    class_: str = Field(..., alias="class")

class ClassUpdateCountsRequest(BaseModel):
    class_: str = Field(..., alias="class")
    countField: str
    value: str

class ClassUpdateIsCountedByRequest(BaseModel):
    class_: str = Field(..., alias="class")
    dayIdentifier: str
    value: str

@router.get("/api/classes")
def list_classes(request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info
    student_cookie = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)

    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    is_logged_in = False
    if session_cookie:
        if session_cookie == VALID_SESSION_VALUE:
            is_logged_in = True
        elif session_cookie in active_sessions:
            is_logged_in = True

    if not is_logged_in:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not (user_role in [ADMIN_ROLE, TEACHER_ROLE] or student_cookie):
        raise HTTPException(status_code=403, detail="Forbidden: Access to this resource is restricted for your account type.")

    with data_lock:
        return class_data_store

@router.post("/api/classes/add")
def add_class(data: ClassAddRequest, admin_user: dict = Depends(get_current_admin_user)):
    class_name = data.class_
    teacher = data.teacher
    counts1 = data.counts1
    counts2 = data.counts2
    counts3 = data.counts3

    if counts1 not in ['T', 'F'] or counts2 not in ['T', 'F'] or counts3 not in ['T', 'F']:
        raise HTTPException(status_code=400, detail="Invalid counts values (must be T or F)")

    with data_lock:
        if any(c['class'] == class_name for c in class_data_store):
             raise HTTPException(status_code=409, detail=f"Class '{class_name}' already exists.")

        new_class = {
            "class": class_name, "teacher": teacher,
            "counts1": counts1, "counts2": counts2, "counts3": counts3,
            "iscountedby1": data.iscountedby1, "iscountedby2": data.iscountedby2,
            "iscountedby3": data.iscountedby3
        }
        class_data_store.append(new_class)
        class_data_store.sort(key=lambda x: x['class'])

        if save_class_data_to_db():
            return {"success": True, "message": f"Class '{class_name}' added successfully."}
        else:
             # Try to remove if failed
             try:
                 class_data_store.remove(new_class)
             except ValueError:
                 pass
             raise HTTPException(status_code=500, detail=f"Failed to save class '{class_name}' to file.")

@router.post("/api/classes/remove")
def remove_class(data: ClassRemoveRequest, admin_user: dict = Depends(get_current_admin_user)):
    class_name_to_remove = data.class_

    with data_lock:
        original_len = len(class_data_store)
        new_store = [c for c in class_data_store if c['class'] != class_name_to_remove]

        if len(new_store) < original_len:
            class_data_store[:] = new_store
            if save_class_data_to_db():
                return {"success": True, "message": f"Class '{class_name_to_remove}' removed successfully."}
            else:
                 raise HTTPException(status_code=500, detail=f"Class '{class_name_to_remove}' removed from memory, but FAILED to save to file.")
        else:
             raise HTTPException(status_code=404, detail=f"Class '{class_name_to_remove}' not found.")

@router.post("/api/classes/update_counts")
def update_counts(data: ClassUpdateCountsRequest, admin_user: dict = Depends(get_current_admin_user)):
    class_name = data.class_
    count_field = data.countField
    new_value = data.value

    valid_count_fields = ["counts1", "counts2", "counts3"]
    if count_field not in valid_count_fields:
        raise HTTPException(status_code=400, detail=f"Invalid countField. Must be one of {valid_count_fields}")

    if new_value not in ['T', 'F']:
        raise HTTPException(status_code=400, detail="Invalid value. Must be 'T' or 'F'")

    with data_lock:
        class_to_update = next((cls_item for cls_item in class_data_store if cls_item['class'] == class_name), None)

        if not class_to_update:
             raise HTTPException(status_code=404, detail=f"Class '{class_name}' not found.")

        class_to_update[count_field] = new_value
        if save_class_data_to_db():
            return {"success": True, "message": f"Count '{count_field}' for class '{class_name}' updated to '{new_value}'."}
        else:
             raise HTTPException(status_code=500, detail=f"Count for class '{class_name}' updated in memory, but FAILED to save to file.")



@router.post("/api/classes/update_iscountedby")
def update_iscountedby(data: ClassUpdateIsCountedByRequest, request: Request, user_info=Depends(get_current_user_info)):

    user_key, user_role = user_info

    # Check session
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    is_logged_in = False
    if session_cookie:
        if session_cookie == VALID_SESSION_VALUE:
            is_logged_in = True
        elif session_cookie in active_sessions:
            is_logged_in = True

    if not is_logged_in:
        raise HTTPException(status_code=401, detail="Authentication required")

    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
         raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    class_name_to_update = data.class_
    day_identifier = data.dayIdentifier
    new_value = data.value

    if day_identifier not in ['1', '2', '3']:
        raise HTTPException(status_code=400, detail="Invalid dayIdentifier. Must be '1', '2', or '3'.")

    field_to_update = f"iscountedby{day_identifier}"

    # Check config
    allow_self_count_str = 'true'
    config_file_path = DATA_DIR / 'config.json'
    try:
        if config_file_path.is_file():
            with open(config_file_path, 'r', encoding='utf-8') as f:
                current_config_on_disk = json.load(f)
            allow_self_count_str = current_config_on_disk.get('can_students_count_their_own_class', 'true')
    except:
        pass

    allow_self_count = allow_self_count_str.lower() == 'true'

    if not allow_self_count and new_value == class_name_to_update:
        raise HTTPException(status_code=400, detail=f"Configuration prevents class '{class_name_to_update}' from counting itself.")

    with data_lock:
        class_found = False
        for cls_item in class_data_store:
            if cls_item['class'] == class_name_to_update:
                cls_item[field_to_update] = new_value
                class_found = True
                break

        if not class_found:
             raise HTTPException(status_code=404, detail=f"Class '{class_name_to_update}' not found.")

        if save_class_data_to_db():
            return {"success": True, "message": f"Assignment for class '{class_name_to_update}' on day {day_identifier} updated to '{new_value}' and saved."}
        else:
             raise HTTPException(status_code=500, detail=f"Assignment for class '{class_name_to_update}' updated in memory, but FAILED to save to file.")

@router.post("/api/classes/prefill")
def prefill_classes(admin_user: dict = Depends(get_current_admin_user)):
    """
    Scrape website for classes and teachers, and prefill the database.
    Merge with existing classes.
    """
    import html
    
    with data_lock:
        scrape_url = server_config.get('scrape_classes_url')
        if not scrape_url:
            raise HTTPException(status_code=400, detail="Scrape URL not configured.")

        # Create a snapshot for rollback
        snapshot = [c.copy() for c in class_data_store]
        
        try:
            logger.info(f"Scraping classes from {scrape_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(scrape_url, headers=headers, timeout=10)
            response.raise_for_status()
            content = response.text

            # Regex to find classes and teachers in table structure
            # Structure matches: <td width="76">1.A</td><td width="253">Mgr. Kateřina Freislebenová</td>
            pattern = r'<td[^>]*>\s*(\d+\.[A-Z])\s*</td>\s*<td[^>]*>\s*(.*?)\s*</td>'
            
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            
            if not matches:
                # Fallback: Try finding just classes if table structure fails
                found_classes_simple = sorted(list(set(re.findall(r'\b\d+\.[A-Z]\b', content))))
                if not found_classes_simple:
                     raise HTTPException(status_code=404, detail="No classes found at the URL.")
                matches = [(c, "") for c in found_classes_simple]

            classes_updated_count = 0
            classes_added_count = 0

            # Filter duplicates and clean data
            scraped_data = {}
            for cls_name, teacher_raw in matches:
                teacher_clean = re.sub(r'<[^>]+>', '', teacher_raw)
                teacher_clean = html.unescape(teacher_clean).strip()
                scraped_data[cls_name] = teacher_clean
            
            classes_found_count = len(scraped_data)

            existing_class_map = {c['class']: c for c in class_data_store}
            
            for cls_name, teacher in scraped_data.items():
                if cls_name in existing_class_map:
                    # Update teacher if currently empty
                    current_entry = existing_class_map[cls_name]
                    if not current_entry.get('teacher'):
                        current_entry['teacher'] = teacher
                        classes_updated_count += 1
                else:
                    new_class = {
                        "class": cls_name,
                        "teacher": teacher, 
                        "counts1": "F",
                        "counts2": "F",
                        "counts3": "F",
                        "iscountedby1": "_NULL_",
                        "iscountedby2": "_NULL_",
                        "iscountedby3": "_NULL_"
                    }
                    class_data_store.append(new_class)
                    classes_added_count += 1

            if classes_updated_count == 0 and classes_added_count == 0:
                 return {"success": True, "message": "No new classes or teacher updates found.", "classes": class_data_store}

            class_data_store.sort(key=lambda x: x['class'])

            if save_class_data_to_db():
                msg = f"Found {classes_found_count} classes. Added {classes_added_count} new, updated {classes_updated_count} teachers."
                return {"success": True, "message": msg, "classes": class_data_store}
            else:
                # Rollback
                class_data_store[:] = snapshot
                raise HTTPException(status_code=500, detail="Failed to save data.")

        except requests.RequestException as e:
            logger.error(f"Network error scraping classes: {e}")
            raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error scraping classes: {e}")
            class_data_store[:] = snapshot
            raise HTTPException(status_code=500, detail=f"Scrape failed: {str(e)}")

class BatchUpdateItem(BaseModel):
    class_: str = Field(..., alias="class")
    dayIdentifier: str
    value: str

class ClassUpdateIsCountedByBatchRequest(BaseModel):
    updates: list[BatchUpdateItem]

@router.post("/api/classes/update_iscountedby_batch")
def update_iscountedby_batch(data: ClassUpdateIsCountedByBatchRequest, request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info

    # Check session
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    is_logged_in = False
    if session_cookie:
        if session_cookie == VALID_SESSION_VALUE:
            is_logged_in = True
        elif session_cookie in active_sessions:
            is_logged_in = True

    if not is_logged_in:
        raise HTTPException(status_code=401, detail="Authentication required")

    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
         raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    updates = data.updates
    if not updates:
        return {"success": True, "message": "No updates provided."}

    # Check config once
    allow_self_count_str = 'true'
    config_file_path = DATA_DIR / 'config.json'
    try:
        if config_file_path.is_file():
            with open(config_file_path, 'r', encoding='utf-8') as f:
                current_config_on_disk = json.load(f)
            allow_self_count_str = current_config_on_disk.get('can_students_count_their_own_class', 'true')
    except:
        pass
    
    allow_self_count = allow_self_count_str.lower() != 'false'

    with data_lock:
        updated_count = 0
        for update in updates:
            class_name = update.class_
            day_identifier = update.dayIdentifier
            new_value = update.value

            if day_identifier not in ['1', '2', '3']:
                continue 

            if not allow_self_count and new_value == class_name:
                continue # Skip invalid self-assignment based on config

            field_to_update = f"iscountedby{day_identifier}"
            
            for cls_item in class_data_store:
                if cls_item['class'] == class_name:
                    cls_item[field_to_update] = new_value
                    updated_count += 1
                    break
        
        if updated_count > 0:
            if save_class_data_to_db():
                return {"success": True, "message": f"Updated {updated_count} assignments."}
            else:
                raise HTTPException(status_code=500, detail="Failed to save data.")
        else:
            return {"success": True, "message": "No changes made."}
