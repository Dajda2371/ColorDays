import re
import requests
import logging
from data_manager import class_data_store, save_class_data_to_db, server_config, data_lock

logger = logging.getLogger('ColorDaysLogger')

def handle_api_classes_prefill(handler, data):
    """
    Handler to scrape website for classes and prefill the database.
    Only works if the class list is currently empty.
    """
    with data_lock:
        scrape_url = server_config.get('scrape_classes_url')
        if not scrape_url:
            handler._send_response(400, {"error": "Scrape URL not configured."})
            return

        try:
            logger.info(f"Scraping classes from {scrape_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(scrape_url, headers=headers, timeout=10)
            response.raise_for_status()
            content = response.text

            # Regex to find classes like 1.A, 9.B.
            found_classes = sorted(list(set(re.findall(r'\b\d+\.[A-Z]\b', content))))
            
            if not found_classes:
                 handler._send_response(404, {"error": "No classes matching format 'N.X' found at the URL."})
                 return

            # Get set of existing class names
            existing_class_names = {c['class'] for c in class_data_store}
            
            # Filter found classes to only new ones
            new_classes_to_add = [c for c in found_classes if c not in existing_class_names]

            if not new_classes_to_add:
                 handler._send_response(200, {"success": True, "message": "No new classes found to add.", "classes": []})
                 return

            new_class_entries = []
            for cls_name in new_classes_to_add:
                new_class_entries.append({
                    "class": cls_name,
                    "teacher": "", 
                    "counts1": "F",
                    "counts2": "F",
                    "counts3": "F",
                    "iscountedby1": "_NULL_",
                    "iscountedby2": "_NULL_",
                    "iscountedby3": "_NULL_"
                })
            
            class_data_store.extend(new_class_entries)
            if save_class_data_to_db():
                handler._send_response(200, {"success": True, "message": f"Successfully added {len(new_class_entries)} new classes.", "classes": new_class_entries})
            else:
                 # Rollback memory change if DB save fails
                # Note: This is a simple rollback, removing the last N items. 
                # Ideally we should be more robust, but for this simpler script:
                for _ in range(len(new_class_entries)):
                    class_data_store.pop() 
                handler._send_response(500, {"error": "Failed to save data to database."})

        except requests.RequestException as e:
            logger.error(f"Network error scraping classes: {e}")
            handler._send_response(500, {"error": f"Network error during scrape: {str(e)}"})
        except Exception as e:
            logger.error(f"Error scraping classes: {e}")
            handler._send_response(500, {"error": f"Failed to scrape classes: {str(e)}"})
