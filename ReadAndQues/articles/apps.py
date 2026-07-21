from django.apps import AppConfig


class ArticlesConfig(AppConfig):
    name = 'articles'

    def ready(self):
        try:
            from database.BM25.connection import rebuild_index
            rebuild_index()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"BM25 index skipped at startup: {e}")
