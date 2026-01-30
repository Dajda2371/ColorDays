
from .auth.login import handle_login
from .auth.login_student import handle_login_student
from .auth.logout import handle_logout
from .auth.auth_change import handle_auth_change
from .users.users import handle_api_users_post
from .users.users_remove import handle_api_users_remove
from .users.users_set import handle_api_users_set
from .classes.classes_add import handle_api_classes_add
from .classes.classes_remove import handle_api_classes_remove
from .classes.classes_update_counts import handle_api_classes_update_counts
from .classes.classes_update_iscountedby import handle_api_classes_update_iscountedby
from .students.students_add import handle_api_students_add
from .students.students_remove import handle_api_students_remove
from .students.student_update_counting_class import handle_api_student_update_counting_class
from .counts.increment import handle_api_increment
from .counts.decrement import handle_api_decrement
from .config.data_save_config import handle_api_data_save_config
from .config.language_set import handle_api_language_set
from .classes.classes_prefill import handle_api_classes_prefill

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
    '/api/classes/prefill': handle_api_classes_prefill,
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
