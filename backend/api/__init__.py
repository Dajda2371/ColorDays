"""API endpoint handlers for ColorDays application.

This module provides access to both GET and POST route mappings
for easy integration with server.py.
"""

# Import GET routes from the get/ directory
from api.get import GET_ROUTES

# Import POST routes from the post/ directory
from api.post import POST_ROUTES

__all__ = ['GET_ROUTES', 'POST_ROUTES']
