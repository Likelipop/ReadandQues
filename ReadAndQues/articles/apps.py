import os

from django.apps import AppConfig


class ArticlesConfig(AppConfig):
    name = "articles"

    def ready(self):
        # Skip BM25 rebuild in Gunicorn forked worker processes.
        # Gunicorn sets the worker pid after forking; the arbiter (main) process
        # does NOT set this env var.  We only want one rebuild in the arbiter so
        # that each forked worker inherits the shared index via copy-on-write.
        # When running under manage.py (runserver / migrate / shell) the var is
        # also absent, so index build still happens normally there.
        if os.environ.get("_GUNICORN_WORKER"):
            return

        try:
            from database.BM25.connection import rebuild_index

            rebuild_index()
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"BM25 index skipped at startup: {e}")
