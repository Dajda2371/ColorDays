from fastapi import APIRouter, Depends, HTTPException, Request
from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME
from dependencies import get_current_user_info
from data_manager import class_data_store, load_counts_from_db

router = APIRouter()

@router.get("/api/leaderboard")
def get_leaderboard(request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info

    is_student_session = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME) is not None

    if not user_key and not is_student_session:
         raise HTTPException(status_code=401, detail="Authentication required")

    # Allow access to Admin, Teacher, and Student
    if not (user_role in [ADMIN_ROLE, TEACHER_ROLE] or is_student_session):
        raise HTTPException(status_code=403, detail="Forbidden: Access denied.")

    # Initialize scores and people count for all classes
    scores = {cls['class']: {'score': 0, 'students': 0, 'teachers': 0} for cls in class_data_store}

    days = ["monday", "tuesday", "wednesday"]

    for day in days:
        try:
            day_counts = load_counts_from_db(day)
            # day_counts structure: temp_data[class_name][type][points] = count

            for class_name, type_data in day_counts.items():
                if class_name in scores:
                    class_score = 0
                    class_students = 0
                    class_teachers = 0
                    for type_val, points_data in type_data.items():
                        for points_val, count in points_data.items():
                            if type_val == 'student':
                                class_score += points_val * count
                                class_students += count
                            elif type_val == 'teacher':
                                class_score += (points_val * count) * 2
                                class_teachers += count
                    scores[class_name]['score'] += class_score
                    scores[class_name]['students'] += class_students
                    scores[class_name]['teachers'] += class_teachers
        except Exception as e:
            print(f"Error loading counts for {day}: {e}")
            # Continue to next day, or maybe raise error? prefer continue to show partial results

    # Convert to list and sort
    leaderboard_data = []
    for k, v in scores.items():
        score = v['score']
        students = v['students']
        teachers = v['teachers']
        divisor = (students * 6) + (teachers * 12)
        if divisor > 0:
            # As requested: total class points / ((number of students * 6) + (number of teachers * 12))
            percentage = round((score / divisor) * 100, 2)
        else:
            percentage = 0
            
        leaderboard_data.append({
            "class": k,
            "score": score,
            "people": students + teachers,
            "percentage": f"{percentage}%"
        })

    leaderboard_data.sort(key=lambda x: float(x["percentage"].replace('%', '')), reverse=True)

    return leaderboard_data
