from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional, List
from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME, SESSION_COOKIE_NAME, VALID_SESSION_VALUE
from data_manager import load_counts_from_db, save_counts_to_db, is_student_allowed
from dependencies import get_current_user_info, active_sessions
import collections


router = APIRouter()

class CountUpdateRequest(BaseModel):
    className: str
    type: str
    points: int
    day: str


@router.post("/api/increment")
def increment_count(data: CountUpdateRequest, request: Request):
    class_name = data.className
    type_val = data.type
    points_val = data.points
    day_identifier = data.day

    if type_val not in ['student', 'teacher']:
         raise HTTPException(status_code=400, detail="Invalid type")
    if not (0 <= points_val <= 6):
         raise HTTPException(status_code=400, detail="Invalid points value")
    if day_identifier.lower() not in ['monday', 'tuesday', 'wednesday']:
         raise HTTPException(status_code=400, detail="Invalid day. Must be one of monday, tuesday, wednesday")

    student_cookie = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
    if student_cookie:
         if not is_student_allowed(student_cookie, class_name, day_identifier.lower()):
             raise HTTPException(status_code=403, detail="Forbidden: You are not authorized to modify counts for this class/day.")

    try:
        day_specific_data = load_counts_from_db(day_identifier.lower())

        if class_name not in day_specific_data:
             day_specific_data[class_name] = collections.defaultdict(lambda: collections.defaultdict(int))
             for t in ['student', 'teacher']:
                for p in range(7):
                    day_specific_data[class_name][t][p] = 0

        current_count = day_specific_data[class_name][type_val][points_val]
        day_specific_data[class_name][type_val][points_val] = current_count + 1

        if save_counts_to_db(day_identifier.lower(), day_specific_data):
            return {"success": True, "message": f"Count incremented for {day_identifier}"}
        else:
             raise HTTPException(status_code=500, detail="Failed to save to database")
    except Exception as e:
         raise HTTPException(status_code=500, detail="Internal server error")
