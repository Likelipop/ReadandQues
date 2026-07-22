import os
import sys
from pathlib import Path

from celery import Celery

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = PROJECT_ROOT / 'ReadAndQues'
for candidate in (str(PROJECT_ROOT), str(APP_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ReadAndQues.settings_prod')

app = Celery('worker_service')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(packages=['worker_service.tasks', 'worker_service'])

from . import tasks  # noqa: F401
