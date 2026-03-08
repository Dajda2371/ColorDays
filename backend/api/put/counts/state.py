from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME
from dependencies import get_current_user_info
from data_manager import class_data_store, save_class_data_to_db, is_student_allowed

router = APIRouter()

class StateRequest(BaseModel):
    className: str
    day: str
    state: str # 'done' or 'locked' or ''

@router.put("/api/counts/state")
def update_state(request: Request, payload: StateRequest):
    class_name = payload.className
    day_identifier = payload.day
    new_state = payload.state

    if new_state not in ['done', 'locked', '']:
         raise HTTPException(status_code=400, detail="Invalid state")
    if day_identifier.lower() not in ['monday', 'tuesday', 'wednesday']:
         raise HTTPException(status_code=400, detail="Invalid day")

    user_key, user_role = get_current_user_info(request)
    student_auth_cookie = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)

    # Permission check
    if new_state == 'locked':
        if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
            raise HTTPException(status_code=403, detail="Only teachers and admins can lock.")
    elif new_state == 'done':
        # Everyone can mark as done if they have access to count
        allowed = False
        if user_role in [ADMIN_ROLE, TEACHER_ROLE]:
            allowed = True
        elif student_auth_cookie:
            if is_student_allowed(student_auth_cookie, class_name, day_identifier.lower()):
                allowed = True
        if not allowed:
            raise HTTPException(status_code=403, detail="Forbidden: You are not authorized to mark this class as done.")
    elif new_state == '':
        # Resetting state
        if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
            raise HTTPException(status_code=403, detail="Only teachers and admins can reset state.")

    # Find the class and update
    day_num = {'monday': '1', 'tuesday': '2', 'wednesday': '3'}[day_identifier.lower()]
    state_key = f'state{day_num}'

    class_found = False
    for cls in class_data_store:
        if cls['class'] == class_name:
            cls[state_key] = new_state
            class_found = True
            break
    
    if not class_found:
        raise HTTPException(status_code=404, detail="Class not found")

    if save_class_data_to_db():
        return {"success": True, "state": new_state}
    else:
        raise HTTPException(status_code=500, detail="Failed to save state to database")
