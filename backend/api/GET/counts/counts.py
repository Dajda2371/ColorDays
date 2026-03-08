from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Optional
from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME
from dependencies import get_current_user_info
from data_manager import load_counts_from_db, is_student_allowed

router = APIRouter()

@router.get("/api/counts")
def get_counts(
    request: Request,
    class_name: str = Query(..., alias="class"),
    day: str = Query(..., alias="day"),
    user_info=Depends(get_current_user_info)
):
    user_key, user_role = user_info

    is_student_session_for_counts = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME) is not None
    
    if not user_key and not is_student_session_for_counts:
         raise HTTPException(status_code=401, detail="Authentication required")

    if not (user_role in [ADMIN_ROLE, TEACHER_ROLE] or is_student_session_for_counts):
        raise HTTPException(status_code=403, detail="Forbidden: Access denied for your role.")

    if is_student_session_for_counts:
        student_auth_cookie_for_counts = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
        student_code = student_auth_cookie_for_counts  # It's the string value in FastAPI cookie dict
        if not is_student_allowed(student_code, class_name, day.lower()):
            raise HTTPException(status_code=403, detail="Forbidden: You are not authorized to view counts for this class/day.")

    response_data = []
    try:
        from data_manager import class_data_store
        state = ""
        day_num = {'monday': '1', 'tuesday': '2', 'wednesday': '3'}.get(day.lower(), '1')
        state_key = f"state{day_num}"
        cls_info = next((c for c in class_data_store if c['class'] == class_name), None)
        if cls_info:
            state = cls_info.get(state_key, "")

        day_specific_loaded_data = load_counts_from_db(day)

        rows = []
        if class_name in day_specific_loaded_data:
            class_day_data = day_specific_loaded_data[class_name]
            for type_val in ['student', 'teacher']:
                for points_val in range(7):
                    count = class_day_data.get(type_val, {}).get(points_val, 0)
                    rows.append({"type": type_val, "points": points_val, "count": count})
            rows.sort(key=lambda x: (x['type'], x['points']))
        else:
            for type_val in ['student', 'teacher']:
                for points_val in range(7):
                     rows.append({"type": type_val, "points": points_val, "count": 0})
        
        return {"counts": rows, "state": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Server error fetching counts.")
