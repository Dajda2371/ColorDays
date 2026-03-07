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
    scores = {cls['class']: {'score': 0, 'people': 0} for cls in class_data_store}

    days = ["monday", "tuesday", "wednesday"]

    for day in days:
        try:
            day_counts = load_counts_from_db(day)
            # day_counts structure: temp_data[class_name][type][points] = count

            for class_name, type_data in day_counts.items():
                if class_name in scores:
                    class_score = 0
                    class_people = 0
                    for type_val, points_data in type_data.items():
                        for points_val, count in points_data.items():
                            class_score += points_val * count
                            class_people += count
                    scores[class_name]['score'] += class_score
                    scores[class_name]['people'] += class_people
        except Exception as e:
            print(f"Error loading counts for {day}: {e}")
            # Continue to next day, or maybe raise error? prefer continue to show partial results

    # Convert to list and sort
    leaderboard_data = []
    for k, v in scores.items():
        score = v['score']
        people = v['people']
        if score > 0:
            # As requested: total students + teachers (people) divided by total class points (score)
            percentage = round((people / score) * 100, 2)
        else:
            percentage = 0
            
        leaderboard_data.append({
            "class": k,
            "score": score,
            "people": people,
            "percentage": f"{percentage}%"
        })

    leaderboard_data.sort(key=lambda x: x["score"], reverse=True)

    return leaderboard_data
