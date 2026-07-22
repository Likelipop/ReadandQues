"""
articles/services/user_stars.py — User Star management logic.
"""

import logging
from typing import Tuple

from accounts.models import UserProfile
from django.db import transaction

logger = logging.getLogger(__name__)


def deduct_user_star(user) -> Tuple[bool, str]:
    """
    Atomically deducts one star from the user's profile.
    Returns (success, error_message).
    """
    try:
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(user=user)
            if profile.stars <= 0:
                return False, "NO_STARS"

            profile.stars -= 1
            profile.save()
            return True, ""
    except Exception as e:
        logger.error(f"Error deducting star for user {user.id}: {e}")
        return False, "Lỗi hệ thống khi cập nhật số lượng Star."


def refund_user_star(user):
    """
    Atomically refunds one star to the user's profile.
    """
    try:
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(user=user)
            profile.stars += 1
            profile.save()
    except Exception as e:
        logger.error(f"Error refunding star for user {user.id}: {e}")
