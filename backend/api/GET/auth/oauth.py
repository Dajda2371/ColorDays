"""OAuth dependency storage."""

# These will be set by server.py if available
InstalledAppFlow = None
google_discovery_service = None


def set_oauth_dependencies(installed_app_flow, discovery_service):
    """Set OAuth dependencies from server.py.

    Args:
        installed_app_flow: The InstalledAppFlow class from google_auth_oauthlib
        discovery_service: The discovery module from googleapiclient
    """
    global InstalledAppFlow, google_discovery_service
    InstalledAppFlow = installed_app_flow
    google_discovery_service = discovery_service
