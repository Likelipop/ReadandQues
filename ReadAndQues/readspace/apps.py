import os
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ReadspaceConfig(AppConfig):
    name = 'readspace'

    def ready(self):
        if os.environ.get("_GUNICORN_WORKER"):
            return

        try:
            from service.infrastructure.bm25.connection import rebuild_index
            rebuild_index()
        except Exception as e:
            logger.warning(f"BM25 index skipped at startup: {e}")
