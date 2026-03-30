from fastapi import APIRouter, Depends, HTTPException, Request
from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME
from dependencies import get_current_user_info
from data_manager import class_data_store, data_lock, overrides_store

router = APIRouter()

@router.get("/api/classes")
def get_classes(request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info

    # Access cookie directly from request
    is_student_session = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME) is not None

    if not user_key and not is_student_session:
         raise HTTPException(status_code=401, detail="Authentication required")

    if not (user_role in [ADMIN_ROLE, TEACHER_ROLE] or is_student_session):
        raise HTTPException(status_code=403, detail="Forbidden: Access to this resource is restricted for your account type.")

    with data_lock:
        response_data = []
        for cls in class_data_store:
            cls_copy = dict(cls)
            class_name = cls['class']
            for day in ['monday', 'tuesday', 'wednesday']:
                is_override_active = False
                if class_name in overrides_store:
                    day_override = overrides_store[class_name].get(day, {})
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
                        is_override_active = True
                cls_copy[f'override_{day}'] = is_override_active
            response_data.append(cls_copy)
    return response_data
