from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME, SESSION_COOKIE_NAME, VALID_SESSION_VALUE
from data_manager import students_data_store, class_data_store, data_lock, save_students_data_to_db
from dependencies import get_current_user_info, active_sessions
from utils import generate_random_code

router = APIRouter()

class StudentAddRequest(BaseModel):
    class_: str = Field(..., alias="class")
    note: Optional[str] = ""

class StudentRemoveRequest(BaseModel):
    code: str

class StudentUpdateCountingClassRequest(BaseModel):
    student_code: str
    class_name: str
    is_counting: bool

@router.get("/api/students")
def list_students(request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info
    student_cookie = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)

    # Check session
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    is_logged_in = False
    if session_cookie:
        if session_cookie == VALID_SESSION_VALUE:
            is_logged_in = True
        elif session_cookie in active_sessions:
            is_logged_in = True

    if not is_logged_in:
        raise HTTPException(status_code=401, detail="Authentication required")

    is_student_user_session = student_cookie is not None

    response_payload = []
    with data_lock:
        if is_student_user_session:
             student_code = student_cookie
             found_student = next((s for s in students_data_store if s.get('code') == student_code), None)

             if found_student:
                 counting_classes_list = []
                 try:
                     s_str = found_student.get('counts_classes', '[]')
                     if s_str.startswith('[') and s_str.endswith(']'):
                         s_content = s_str[1:-1]
                         if s_content.strip():
                             counting_classes_list = [item.strip() for item in s_content.split(',')]
                 except Exception:
                     pass

                 response_payload.append({**found_student, "counting_classes": counting_classes_list})

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
                except Exception:
                     pass
                response_payload.append({**student_data_item, "counting_classes": counting_classes_list})

    return response_payload

@router.post("/api/students/add")
def add_student(data: StudentAddRequest, request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info
    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    student_class = data.class_
    note = data.note

    with data_lock:
        new_student_config = {
            "code": generate_random_code(),
            "class": student_class,
            "note": note,
            "counts_classes": "[]" # Using counts_classes to match DB schema
        }
        students_data_store.append(new_student_config)
        students_data_store.sort(key=lambda x: (x['class'], x.get('note', '')))

        if save_students_data_to_db():
            return {"success": True, "message": f"Student configuration for class '{student_class}' (Note: '{note}') added successfully."}
        else:
             try:
                 students_data_store.remove(new_student_config)
             except:
                 pass
             raise HTTPException(status_code=500, detail=f"Failed to save new student configuration for '{student_class}' (Note: '{note}') to file.")

@router.post("/api/students/remove")
def remove_student(data: StudentRemoveRequest, request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info
    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    student_code = data.code

    with data_lock:
        original_len = len(students_data_store)
        new_store = [s for s in students_data_store if s.get('code') != student_code]

        if len(new_store) < original_len:
            students_data_store[:] = new_store
            if save_students_data_to_db():
                return {"success": True, "message": f"Student configuration with code '{student_code}' removed successfully."}
            else:
                 raise HTTPException(status_code=500, detail=f"Student configuration with code '{student_code}' removed from memory, but FAILED to save to file.")
        else:
             raise HTTPException(status_code=404, detail=f"Student configuration with code '{student_code}' not found.")

@router.get("/api/student/counting-details")
def get_student_counting_details(
    code: str,
    day: str,
    request: Request,
    user_info=Depends(get_current_user_info)
):
    user_key, user_role = user_info

    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    is_logged_in = False
    if session_cookie and (session_cookie == VALID_SESSION_VALUE or session_cookie in active_sessions):
         is_logged_in = True

    if not is_logged_in:
        raise HTTPException(status_code=401, detail="Authentication required")

    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    if day not in ['1', '2', '3']:
        raise HTTPException(status_code=400, detail="Invalid 'day' parameter. Must be 1, 2, or 3.")

    with data_lock:
        target_student = next((s for s in students_data_store if s.get('code') == code), None)

        if not target_student:
             raise HTTPException(status_code=404, detail=f"Student configuration with code '{code}' not found.")

        student_main_class = target_student.get('class')
        if not student_main_class:
             raise HTTPException(status_code=500, detail=f"Student with code '{code}' has no class assigned.")

        is_counted_by_field = f"iscountedby{day}"
        response_payload = []

        counts_str = target_student.get('counts_classes', '[]')
        student_personal_counts_set = set()
        try:
             if counts_str.startswith('[') and counts_str.endswith(']'):
                 content = counts_str[1:-1]
                 if content.strip():
                     student_personal_counts_set = {c.strip() for c in content.split(',') if c.strip()}
        except:
            pass

        for class_being_evaluated in class_data_store:
            if class_being_evaluated.get(is_counted_by_field) == student_main_class:
                class_to_display_name = class_being_evaluated['class']
                student_is_counting_this_class = class_to_display_name in student_personal_counts_set
                also_counted_by_notes = []

                for other_student in students_data_store:
                    if other_student.get('code') == code:
                        continue

                    other_counts_str = other_student.get('counts_classes', '[]')
                    try:
                        if other_counts_str.startswith('[') and other_counts_str.endswith(']'):
                             other_content = other_counts_str[1:-1]
                             if other_content.strip():
                                 if class_to_display_name in {c.strip() for c in other_content.split(',') if c.strip()}:
                                     also_counted_by_notes.append(other_student.get('note', 'Unknown Note'))
                    except:
                        pass

                response_payload.append({
                    "class_name": class_to_display_name,
                    "is_counted_by_current_student": student_is_counting_this_class,
                    "also_counted_by_notes": sorted(list(set(also_counted_by_notes)))
                })

        final_response = {
            "student_note": target_student.get('note', ''),
            "student_class": target_student.get('class', ''),
            "counting_details": sorted(response_payload, key=lambda x: x['class_name'])
        }

    return final_response

@router.post("/api/student/update-counting-class")
def update_counting_class(data: StudentUpdateCountingClassRequest, request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info

    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
         raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    student_code = data.student_code
    class_name = data.class_name
    is_counting = data.is_counting

    with data_lock:
        target_student = next((s for s in students_data_store if s.get('code') == student_code), None)

        if not target_student:
             raise HTTPException(status_code=404, detail=f"Student configuration with code '{student_code}' not found.")

        student_note = target_student.get('note', student_code)
        counts_str = target_student.get('counts_classes', '[]')
        current_counts_set = set()

        try:
            if counts_str.startswith('[') and counts_str.endswith(']'):
                content = counts_str[1:-1]
                if content.strip():
                    current_counts_set = {c.strip() for c in content.split(',') if c.strip()}
        except:
            pass

        if is_counting:
            current_counts_set.add(class_name)
        else:
            current_counts_set.discard(class_name)

        sorted_list = sorted(list(current_counts_set))
        new_counts_str = f"[{', '.join(sorted_list)}]" if sorted_list else "[]"

        target_student['counts_classes'] = new_counts_str

        if save_students_data_to_db():
            action = "added to" if is_counting else "removed from"
            return {"success": True, "message": f"Class '{class_name}' {action} student '{student_note}'s counting list."}
        else:
             raise HTTPException(status_code=500, detail=f"Failed to save updated counting list for student '{student_note}' to file.")
