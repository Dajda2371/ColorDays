"""GET endpoint handlers for ColorDays API.

This module aggregates all GET endpoint handlers from individual files
organized by category.
"""

from .users import handle_api_users
from .classes import handle_api_classes
from .students import handle_api_students
from .student_counting_details import handle_api_student_counting_details
from .counts import handle_api_counts
from .data_config import handle_api_data_config
from .translations import handle_api_translations
from .login_google import handle_login_google
from .oauth2callback import handle_oauth2callback
from .oauth import set_oauth_dependencies

# Route mapping dictionary
GET_ROUTES = {
    '/api/users': handle_api_users,
    '/api/classes': handle_api_classes,
    '/api/students': handle_api_students,
    '/api/student/counting-details': handle_api_student_counting_details,
    '/api/counts': handle_api_counts,
    '/api/data/config': handle_api_data_config,
    '/api/translations': handle_api_translations,
    '/login/google': handle_login_google,
    '/oauth2callback': handle_oauth2callback,
}

__all__ = ['GET_ROUTES', 'set_oauth_dependencies']
