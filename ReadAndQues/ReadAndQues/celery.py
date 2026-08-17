import os
from celery import Celery

# Set default settings module for Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ReadAndQues.settings.dev")

app = Celery("ReadAndQues")

# Using namespace='CELERY' means all celery-related configuration keys
# should have a `CELERY_` prefix in Django settings.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
