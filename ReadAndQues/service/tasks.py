"""
service/tasks.py — Background Task Dispatcher.
Uses standard daemon threads for lightweight asynchronous background tasks.
"""

import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def run_in_background(func: Callable, *args, **kwargs) -> threading.Thread:
    """
    Executes a function in a background daemon thread.
    """
    def _worker():
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Background task '{func.__name__}' failed: {e}", exc_info=True)

    thread = threading.Thread(
        target=_worker,
        name=f"BackgroundTask-{func.__name__}",
        daemon=True,
    )
    thread.start()
    logger.info(f"Spawned background thread for '{func.__name__}'")
    return thread
