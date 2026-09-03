"""
service/infrastructure/utils.py — Infrastructure utilities & centralized error boundaries.
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


def db_safe(default_return: Any = None) -> Callable:
    """
    Decorator for Infrastructure methods:
    - Catches all DB/infrastructure exceptions.
    - Logs traceback with exc_info=True.
    - Returns default_return safely.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"❌ DB Boundary Exception in '{func.__qualname__}': {e}",
                    exc_info=True,
                )
                return default_return

        return wrapper

    return decorator
