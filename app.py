#!/usr/bin/env python3
"""
Gunicorn entry point for Railway/production deployment
Imports the Flask app from src.api.app
"""
from src.api.app import app

if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', 5000))
    is_production = os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('DO_APP_NAME')
    app.run(debug=not is_production, port=port, host='0.0.0.0')
