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

    # Find the class first to get current state
    day_num = {'monday': '1', 'tuesday': '2', 'wednesday': '3'}[day_identifier.lower()]
    state_key = f'state{day_num}'
    
    class_found = False
    current_state = ''
    target_cls = None
    for cls in class_data_store:
        if cls['class'] == class_name:
            current_state = cls.get(state_key, '')
            target_cls = cls
            class_found = True
            break
            
    if not class_found:
        raise HTTPException(status_code=404, detail="Class not found")

    # Permission check
    if new_state == 'locked':
        if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
            raise HTTPException(status_code=403, detail="Only teachers and admins can lock.")
    elif new_state == 'done' or new_state == '':
        # If it is currently locked and they try to set it to '' or 'done', only teachers can do that
        if current_state == 'locked' and user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
            raise HTTPException(status_code=403, detail="Only teachers and admins can unlock a class.")

        # Everyone can mark as done or edit (reset) if they have access to count
        allowed = False
        if user_role in [ADMIN_ROLE, TEACHER_ROLE]:
            allowed = True
        elif student_auth_cookie:
            if is_student_allowed(student_auth_cookie, class_name, day_identifier.lower()):
                allowed = True
        if not allowed:
            raise HTTPException(status_code=403, detail="Forbidden: You are not authorized to modify this class's state.")

    target_cls[state_key] = new_state

    if save_class_data_to_db():
        return {"success": True, "state": new_state}
    else:
        raise HTTPException(status_code=500, detail="Failed to save state to database")
