from fastapi import APIRouter, Depends, HTTPException, Request
from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME
from dependencies import get_current_user_info
from data_manager import students_data_store, data_lock

router = APIRouter()

@router.get("/api/students")
def get_students(request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info
    
    student_auth_cookie = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)
    is_student_user_session = student_auth_cookie is not None

    if not user_key and not is_student_user_session:
         raise HTTPException(status_code=401, detail="Authentication required")

    response_payload = []
    with data_lock:
        if is_student_user_session:
            student_code_from_cookie = student_auth_cookie
            found_student_data_item = None
            for s_data_item in students_data_store:
                if s_data_item.get('code') == student_code_from_cookie:
                    found_student_data_item = s_data_item
                    break

            if found_student_data_item:
                counting_classes_list = []
                try:
                    s_str = found_student_data_item.get('counts_classes', '[]')
                    if s_str.startswith('[') and s_str.endswith(']'):
                        s_content = s_str[1:-1]
                        if s_content.strip():
                            counting_classes_list = [item.strip() for item in s_content.split(',')]
                except Exception as e:
                    print(f"Error parsing counts_classes: {e}")

                response_payload.append({**found_student_data_item, "counting_classes": counting_classes_list})

        else:
            if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
                raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

            for student_data_item in students_data_store:
                counting_classes_list = []
                try:
                    s_str = student_data_item.get('counts_classes', '[]')
                    if s_str.startswith('[') and s_str.endswith(']'):
                        s_content = s_str[1:-1]
                        if s_content.strip():
                            counting_classes_list = [item.strip() for item in s_content.split(',')]
                except Exception as e:
                    print(f"Error parsing counts_classes: {e}")
                response_payload.append({**student_data_item, "counting_classes": counting_classes_list})

    return response_payload
