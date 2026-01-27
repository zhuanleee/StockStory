"""
Web API

Flask application for REST API and webhooks.
"""

from src.api.app import app, create_app

__all__ = ['app', 'create_app']
