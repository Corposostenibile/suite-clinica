"""
Routes module for SuiteMind blueprint.
Contains all route handlers organized by functionality.
"""

# main_routes removed - no HTML endpoints served
from .api_routes import register_api_routes

__all__ = [
    'register_api_routes'
]