"""Celery application for the AI API Gateway admin portal.

Autodiscovers tasks from all installed Django apps.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin_portal.settings")

app = Celery("admin_portal")

# Read configuration from Django settings using the CELERY_ namespace
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks in all INSTALLED_APPS
app.autodiscover_tasks()
