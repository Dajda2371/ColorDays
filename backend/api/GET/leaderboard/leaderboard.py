from fastapi import APIRouter, Depends, HTTPException, Request
from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME
from dependencies import get_current_user_info
from data_manager import class_data_store, load_counts_from_db, overrides_store

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

    # Process overrides
    days = ["monday", "tuesday", "wednesday"]
    for class_name in scores:
        if class_name in overrides_store:
            for day in days:
                day_override = overrides_store[class_name].get(day, {})
                is_checked = day_override.get('checkbox', False)
                try:
                    sp = int(day_override.get('student_points', ''))
                    ns = int(day_override.get('number_of_students', ''))
                    tp = int(day_override.get('teacher_points', ''))
                    nt = int(day_override.get('number_of_teachers', ''))
                    valid_ints = True
                except ValueError:
                    valid_ints = False
                
                if is_checked and valid_ints:
                    # Override active! Replace the normal score with this one.
                    scores[class_name]['score'] += sp + (tp * 2)
                    scores[class_name]['students'] += ns
                    scores[class_name]['teachers'] += nt
                    scores[class_name][f'override_{day}'] = True
                else:
                    scores[class_name][f'override_{day}'] = False

    for day in days:
        try:
            day_counts = load_counts_from_db(day)
            for class_name, type_data in day_counts.items():
                if class_name in scores:
                    if scores[class_name].get(f'override_{day}', False):
                        continue # Skip this day's points since it's overridden
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

    # Convert to list and sort
    leaderboard_data = []

    # Pre-map states for efficiency
    class_states = {cls['class']: (cls.get('state1', ''), cls.get('state2', ''), cls.get('state3', '')) for cls in class_data_store}

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
            
        states = class_states.get(k, ('', '', ''))

        leaderboard_data.append({
            "class": k,
            "score": score,
            "people": students + teachers,
            "percentage": f"{percentage}%",
            "state1": states[0],
            "state2": states[1],
            "state3": states[2]
        })

    leaderboard_data.sort(key=lambda x: float(x["percentage"].replace('%', '')), reverse=True)

    return leaderboard_data
