"""
WSGI entry point for DigitalOcean App Platform

This file is needed because DigitalOcean may auto-detect gunicorn
and try to use it with app:app pattern.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app from the correct location
from src.api.app import app

# This is what gunicorn will look for
application = app

if __name__ == "__main__":
    # Use PORT from environment (Digital Ocean assigns dynamically)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
