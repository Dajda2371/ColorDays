import collections
import traceback
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from config import SQL_AUTH_USER_STUDENT_COOKIE_NAME
from data_manager import load_counts_from_db, save_counts_to_db, is_student_allowed, data_lock

router = APIRouter()

class IncrementRequest(BaseModel):
    class_name: str = Field(alias="class")
    type: str 
    value: int
    day: str

@router.post("/api/decrement")
def decrement_count(request: Request, payload: IncrementRequest): 
    class_name = payload.class_name
    type_val = payload.type
    points_val = payload.value
    day_identifier = payload.day

    if type_val not in ['student', 'teacher']:
         raise HTTPException(status_code=400, detail="Invalid type")
    if not (0 <= points_val <= 6):
         raise HTTPException(status_code=400, detail="Invalid points value")
    if day_identifier.lower() not in ['monday', 'tuesday', 'wednesday']:
         raise HTTPException(status_code=400, detail="Invalid day. Must be one of monday, tuesday, wednesday")

    student_auth_cookie = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
    if student_auth_cookie:
        student_code = student_auth_cookie
        if not is_student_allowed(student_code, class_name, day_identifier.lower()):
             raise HTTPException(status_code=403, detail="Forbidden: You are not authorized to modify counts for this class/day.")

    # Override Check
    from data_manager import overrides_store
    day_override = overrides_store.get(class_name, {}).get(day_identifier.lower(), {})
    is_checked = day_override.get('checkbox', False)
    try:
        int(day_override.get('student_points', ''))
        int(day_override.get('number_of_students', ''))
        int(day_override.get('teacher_points', ''))
        int(day_override.get('number_of_teachers', ''))
        valid_ints = True
    except ValueError:
        valid_ints = False
    
    if is_checked and valid_ints:
        raise HTTPException(status_code=403, detail="Class is overridden by admin for this day. Edits are disabled.")

    # State Check
    from data_manager import class_data_store
    day_num = {'monday': '1', 'tuesday': '2', 'wednesday': '3'}.get(day_identifier.lower(), '1')
    state_key = f"state{day_num}"
    cls_info = next((c for c in class_data_store if c['class'] == class_name), None)
    if cls_info and cls_info.get(state_key):
        current_state = cls_info.get(state_key)
        if current_state == 'locked' and student_auth_cookie:
             raise HTTPException(status_code=403, detail="Forbidden: This class is locked by a teacher and cannot be modified.")
        raise HTTPException(status_code=400, detail=f"Cannot modify data because it is marked as {current_state}.")
    
    try:
        with data_lock:
            day_specific_data = load_counts_from_db(day_identifier.lower())

            if class_name not in day_specific_data:
                day_specific_data[class_name] = collections.defaultdict(lambda: collections.defaultdict(int))
                for t in ['student', 'teacher']:
                    for p in range(7):
                        day_specific_data[class_name][t][p] = 0

            # Note: relying on data structure being compatible with [points_val] int key or auto-string conversion if JSON
            # Need to be safe about the key not existing
            if type_val not in day_specific_data[class_name]:
                 day_specific_data[class_name][type_val] = {}
                 
            current_count = day_specific_data[class_name][type_val].get(points_val, 0)
            day_specific_data[class_name][type_val][points_val] = max(0, current_count - 1)

            if save_counts_to_db(day_identifier.lower(), day_specific_data):
                return {"success": True, "message": f"Count decremented for {day_identifier}"}
            else:
                 raise HTTPException(status_code=500, detail="Failed to save to database")
    except Exception as e:
        print(f"Error during decrement: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
