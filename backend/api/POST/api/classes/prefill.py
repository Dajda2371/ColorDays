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


class BatchUpdateItem(BaseModel):
    class_: str = Field(..., alias="class")
    dayIdentifier: str
    value: str


class ClassUpdateIsCountedByBatchRequest(BaseModel):
    updates: list[BatchUpdateItem]


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
