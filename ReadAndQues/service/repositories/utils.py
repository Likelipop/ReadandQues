"""
service/repositories/utils.py — Repository utilities & centralized error boundaries.
"""

import logging
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)


def db_safe(default_return: Any = None) -> Callable:
    """
    Decorator bọc phương thức Repository:
    - Bắt mọi lỗi hạ tầng từ tầng DB bên dưới.
    - Ghi log vết lỗi (Traceback) đầy đủ với exc_info=True.
    - Trả về giá trị mặc định an toàn (default_return) cho Service layer.
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
