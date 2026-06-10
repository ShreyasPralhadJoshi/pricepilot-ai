"""
WSGI config for pricepilot project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pricepilot.settings")

from pricepilot.bootstrap import ensure_vercel_database

ensure_vercel_database(Path(__file__).resolve().parent.parent)

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
