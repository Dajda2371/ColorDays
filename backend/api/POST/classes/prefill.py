from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
import re
import requests
import html
import logging
from config import ADMIN_ROLE
from dependencies import get_current_admin_user
from data_manager import class_data_store, save_class_data_to_db, server_config, data_lock

logger = logging.getLogger('ColorDaysLogger')

router = APIRouter()

def sort_class_key(class_dict):
    parts = class_dict['class'].split('.')
    if len(parts) == 2 and parts[0].isdigit():
        return (int(parts[0]), parts[1])
    return (999, class_dict['class'])

@router.post("/api/classes/prefill")
def prefill_classes(admin_user: dict = Depends(get_current_admin_user)):
    """
    Handler to scrape website for classes and prefill the database.
    Only works if the class list is currently empty.
    """
    with data_lock:
        scrape_url = server_config.get('scrape_classes_url')
        if not scrape_url:
            return JSONResponse(status_code=400, content={"success": False, "error": "Scrape URL not configured."})
            
        try:
            logger.info(f"Scraping classes from {scrape_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(scrape_url, headers=headers, timeout=10)
            response.raise_for_status()
            content = response.text

            # Apply regex to find classes and their teachers from typical HTML table structure
            matches = re.findall(r'<td[^>]*>\s*(\d+\.[A-Z])\s*</td>\s*<td[^>]*>\s*(.*?)\s*</td>', content, re.IGNORECASE | re.DOTALL)
            
            found_classes_dict = {}
            for cls, t in matches:
                if cls not in found_classes_dict:
                    found_classes_dict[cls] = html.unescape(t).replace(u'\xa0', u' ').strip()
            
            # If the table structure changes but class name structure remains, fallback
            if not found_classes_dict:
                fallback_classes = re.findall(r'\b\d+\.[A-Z]\b', content)
                for cls in fallback_classes:
                    if cls not in found_classes_dict:
                        found_classes_dict[cls] = ""
            
            if not found_classes_dict:
                 return JSONResponse(status_code=404, content={"success": False, "error": "No classes matching format 'N.X' found at the URL."})

            existing_class_names = {c['class'] for c in class_data_store}
            new_classes_to_add = [cls for cls in found_classes_dict.keys() if cls not in existing_class_names]

            if not new_classes_to_add:
                 return {"success": True, "message": "No new classes found to add.", "classes": []}

            new_class_entries = []
            for cls_name in new_classes_to_add:
                new_class_entries.append({
                    "class": cls_name,
                    "teacher": found_classes_dict[cls_name], 
                    "counts1": "F",
                    "counts2": "F",
                    "counts3": "F",
                    "iscountedby1": "_NULL_",
                    "iscountedby2": "_NULL_",
                    "iscountedby3": "_NULL_"
                })
            
            class_data_store.extend(new_class_entries)
            class_data_store.sort(key=sort_class_key)
            
            if save_class_data_to_db():
                return {"success": True, "message": f"Successfully added {len(new_class_entries)} new classes.", "classes": new_class_entries}
            else:
                 # Rollback memory change if DB save fails
                for _ in range(len(new_class_entries)):
                    class_data_store.pop() 
                return JSONResponse(status_code=500, content={"success": False, "error": "Failed to save data to database."})

        except requests.RequestException as e:
            logger.error(f"Network error scraping classes: {e}")
            return JSONResponse(status_code=500, content={"success": False, "error": f"Network error during scrape: {str(e)}"})
        except Exception as e:
            logger.error(f"Error scraping classes: {e}")
            return JSONResponse(status_code=500, content={"success": False, "error": f"Failed to scrape classes: {str(e)}"})

