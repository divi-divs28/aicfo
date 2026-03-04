"""
Routes package.
Import all routers here for easy access.
"""
from .base import router as base_router
from .auth import router as auth_router
from .chat import router as chat_router
from .dashboard import router as dashboard_router
from .dashboard_analytics import router as dashboard_analytics_router
from .admin import router as admin_router
from .email import router as email_router

__all__ = [
    'base_router',
    'auth_router', 
    'chat_router',
    'dashboard_router',
    'dashboard_analytics_router',
    'admin_router',
    'email_router'
]
