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


@router.get("/api/counts")
def get_counts(
    request: Request,
    class_: str = Query(..., alias="class"),
    day: str = Query(..., alias="day"),
    user_info=Depends(get_current_user_info)
):
    user_key, user_role = user_info

    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    is_logged_in = False
    if session_cookie and (session_cookie == VALID_SESSION_VALUE or session_cookie in active_sessions):
         is_logged_in = True

    if not is_logged_in:
        raise HTTPException(status_code=401, detail="Authentication required")

    student_cookie = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
    is_student_session = student_cookie is not None

    if not (user_role in [ADMIN_ROLE, TEACHER_ROLE] or is_student_session):
        raise HTTPException(status_code=403, detail="Forbidden: Access denied for your role.")

    if student_cookie:
        student_code = student_cookie
        if not is_student_allowed(student_code, class_, day.lower()):
             raise HTTPException(status_code=403, detail="Forbidden: You are not authorized to view counts for this class/day.")

    try:
        day_specific_loaded_data = load_counts_from_db(day)
        response_data = []

        if class_ in day_specific_loaded_data:
            class_day_data = day_specific_loaded_data[class_]
            for type_val in ['student', 'teacher']:
                for points_val in range(7):
                    count = class_day_data.get(type_val, {}).get(points_val, 0)
                    response_data.append({"type": type_val, "points": points_val, "count": count})
            response_data.sort(key=lambda x: (x['type'], x['points']))
        else:
             for type_val in ['student', 'teacher']:
                for points_val in range(7):
                     response_data.append({"type": type_val, "points": points_val, "count": 0})
        return response_data
    except Exception as e:
         raise HTTPException(status_code=500, detail="Server error fetching counts.")
