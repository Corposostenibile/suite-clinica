"""
Routes module for SuiteMind blueprint.
Contains all route handlers organized by functionality.
"""

from .main_routes import register_main_routes
from .api_routes import register_api_routes

__all__ = [
    'register_main_routes',
    'register_api_routes'
]