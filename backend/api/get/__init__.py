"""GET endpoint handlers for ColorDays API.

This module aggregates all GET endpoint handlers from individual files
organized by category.
"""

from api.get.users import handle_api_users
from api.get.classes import handle_api_classes
from api.get.students import handle_api_students, handle_api_student_counting_details
from api.get.counts import handle_api_counts
from api.get.config import handle_api_data_config
from api.get.translations import handle_api_translations
from api.get.oauth import handle_login_google, handle_oauth2callback, set_oauth_dependencies

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
