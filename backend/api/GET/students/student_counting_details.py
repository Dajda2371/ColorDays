from fastapi import APIRouter, Depends, HTTPException, Request, Query
from config import ADMIN_ROLE, TEACHER_ROLE
from dependencies import get_current_user_info
from data_manager import students_data_store, class_data_store, data_lock

router = APIRouter()

@router.get("/api/student/counting-details")
def get_student_counting_details(
    code: str, 
    day: str, 
    user_info=Depends(get_current_user_info)
):
    user_key, user_role = user_info

    if not user_key:
        raise HTTPException(status_code=401, detail="Authentication required")
    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
        raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    if day not in ['1', '2', '3']:
        raise HTTPException(status_code=400, detail="Invalid 'day' parameter. Must be 1, 2, or 3.")

    target_student_config = None
    with data_lock:
        for s_config in students_data_store:
            if s_config.get('code') == code:
                target_student_config = s_config
                break

        if not target_student_config:
            raise HTTPException(status_code=404, detail=f"Student configuration with code '{code}' not found.")

        student_main_class_name = target_student_config.get('class')
        if not student_main_class_name:
             raise HTTPException(status_code=500, detail=f"Student with code '{code}' has no class assigned.")

        is_counted_by_field = f"iscountedby{day}"
        response_payload = []

        target_student_personal_counts_str = target_student_config.get('counts_classes', '[]')
        student_personal_counts_set = set()
        import json
        try:
            parsed = json.loads(target_student_personal_counts_str)
            if isinstance(parsed, list):
                student_personal_counts_set = {str(c) for c in parsed}
        except Exception:
            pass

        for class_being_evaluated in class_data_store:
            if class_being_evaluated.get(is_counted_by_field) == student_main_class_name:
                class_to_display_name = class_being_evaluated['class']
                student_is_counting_this_class = class_to_display_name in student_personal_counts_set
                also_counted_by_notes = []
                for other_student_config in students_data_store:
                    if other_student_config.get('code') == code:
                        continue
                    other_student_counts_classes_str = other_student_config.get('counts_classes', '[]')
                    import json
                    try:
                        other_parsed = json.loads(other_student_counts_classes_str)
                        if isinstance(other_parsed, list):
                            if class_to_display_name in {str(c) for c in other_parsed}:
                                also_counted_by_notes.append(other_student_config.get('note', 'Unknown Note'))
                    except Exception:
                        pass

                response_payload.append({
                    "class_name": class_to_display_name,
                    "is_counted_by_current_student": student_is_counting_this_class,
                    "also_counted_by_notes": sorted(list(set(also_counted_by_notes)))
                })

        final_api_response = {
            "student_note": target_student_config.get('note', ''),
            "student_class": target_student_config.get('class', ''),
            "counting_details": sorted(response_payload, key=lambda x: x['class_name'])
        }

    return final_api_response
