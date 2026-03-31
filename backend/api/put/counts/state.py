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
    is_student = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME) is not None

    if new_state == 'locked':
        if is_student or user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
            raise HTTPException(status_code=403, detail="Only teachers and admins can lock a class.")
    elif new_state in ['done', '']:
        # If it is currently locked, students can NEVER change it
        if current_state == 'locked':
            if is_student or user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
                raise HTTPException(status_code=403, detail="Only teachers and admins can unlock a locked class.")

        # Everyone else (verified students or all teachers/admins) can mark as done or edit if not locked
        allowed = False
        if user_role in [ADMIN_ROLE, TEACHER_ROLE]:
            allowed = True
        elif is_student:
             student_auth_cookie = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
             if is_student_allowed(student_auth_cookie, class_name, day_identifier.lower()):
                allowed = True
        
        if not allowed:
            raise HTTPException(status_code=403, detail="Forbidden: You are not authorized to modify this class's state.")

    target_cls[state_key] = new_state

    if save_class_data_to_db():
        return {"success": True, "state": new_state}
    else:
        raise HTTPException(status_code=500, detail="Failed to save state to database")
