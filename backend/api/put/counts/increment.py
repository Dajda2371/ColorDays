import collections
import traceback
from fastapi import APIRouter, HTTPException, Request, Body
from pydantic import BaseModel
from config import SQL_AUTH_USER_STUDENT_COOKIE_NAME
from data_manager import load_counts_from_db, save_counts_to_db, is_student_allowed

router = APIRouter()

class IncrementRequest(BaseModel):
    className: str
    type: str # 'student' or 'teacher'
    points: int
    day: str

@router.put("/api/increment")
def increment_count(request: Request, payload: IncrementRequest):
    class_name = payload.className
    type_val = payload.type
    points_val = payload.points
    day_identifier = payload.day

    if type_val not in ['student', 'teacher']:
         raise HTTPException(status_code=400, detail="Invalid type")
    if not (0 <= points_val <= 6):
         raise HTTPException(status_code=400, detail="Invalid points value")
    if day_identifier.lower() not in ['monday', 'tuesday', 'wednesday']:
         raise HTTPException(status_code=400, detail="Invalid day. Must be one of monday, tuesday, wednesday")

    # Authorization Check
    student_auth_cookie = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
    if student_auth_cookie:
        student_code = student_auth_cookie
        if not is_student_allowed(student_code, class_name, day_identifier.lower()):
             raise HTTPException(status_code=403, detail="Forbidden: You are not authorized to modify counts for this class/day.")

    try:
        day_specific_data = load_counts_from_db(day_identifier.lower())

        if class_name not in day_specific_data:
            day_specific_data[class_name] = collections.defaultdict(lambda: collections.defaultdict(int))
            # Just mimicking original logic structure for init, though defaultdict handles it
            for t in ['student', 'teacher']:
                for p in range(7):
                    day_specific_data[class_name][t][p] = 0

        # Note: relying on data structure being compatible with [points_val] int key or auto-string conversion if JSON
        current_count = day_specific_data[class_name][type_val][points_val]
        day_specific_data[class_name][type_val][points_val] = current_count + 1

        if save_counts_to_db(day_identifier.lower(), day_specific_data):
            return {"success": True, "message": f"Count incremented for {day_identifier}"}
        else:
             raise HTTPException(status_code=500, detail="Failed to save to database")
    except Exception as e:
        print(f"Error during increment: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
