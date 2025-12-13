
from .login import handle_login
from .login_student import handle_login_student
from .logout import handle_logout
from .auth_change import handle_auth_change
from .users_post import handle_api_users_post
from .users_remove import handle_api_users_remove
from .users_set import handle_api_users_set
from .classes_add import handle_api_classes_add
from .classes_remove import handle_api_classes_remove
from .classes_update_counts import handle_api_classes_update_counts
from .classes_update_iscountedby import handle_api_classes_update_iscountedby
from .students_add import handle_api_students_add
from .students_remove import handle_api_students_remove
from .student_update_counting_class import handle_api_student_update_counting_class
from .increment import handle_api_increment
from .decrement import handle_api_decrement
from .data_save_config import handle_api_data_save_config
from .language_set import handle_api_language_set

POST_ROUTES = {
    '/login': handle_login,
    '/login/student': handle_login_student,
    '/logout': handle_logout,
    '/api/auth/change': handle_auth_change,
    '/api/users': handle_api_users_post,
    '/api/users/remove': handle_api_users_remove,
    '/api/users/set': handle_api_users_set,
    '/api/users/reset': handle_api_users_set,  # Alias
    '/api/classes/add': handle_api_classes_add,
    '/api/classes/remove': handle_api_classes_remove,
    '/api/classes/update_counts': handle_api_classes_update_counts,
    '/api/classes/update_iscountedby': handle_api_classes_update_iscountedby,
    '/api/students/add': handle_api_students_add,
    '/api/students/remove': handle_api_students_remove,
    '/api/student/update-counting-class': handle_api_student_update_counting_class,
    '/api/increment': handle_api_increment,
    '/api/decrement': handle_api_decrement,
    '/api/data/save/config': handle_api_data_save_config,
    '/api/language/set': handle_api_language_set,
}
