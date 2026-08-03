import logging
from contextlib import contextmanager
from django.db import transaction
from accounts.models import UserProfile

logger = logging.getLogger(__name__)

class StarDeductionError(Exception):
    pass

@contextmanager
def consume_user_star(user):
    """
    Context manager that deducts a star from the user's profile before execution.
    If any exception occurs inside the 'with' block, it refunds the star.
    Raises StarDeductionError if the user has no stars.
    """
    # 1. Deduct star
    try:
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(user=user)
            if profile.stars <= 0:
                raise StarDeductionError("NO_STARS")
            profile.stars -= 1
            profile.save()
    except StarDeductionError:
        raise
    except Exception as e:
        logger.error(f"Error deducting star for user {user.id}: {e}")
        raise StarDeductionError("System error while updating stars.")

    # 2. Yield to the wrapped block
    try:
        yield
    except Exception as e:
        # 3. Refund star if error occurred inside the block
        try:
            with transaction.atomic():
                profile = UserProfile.objects.select_for_update().get(user=user)
                profile.stars += 1
                profile.save()
        except Exception as refund_err:
            logger.error(f"Error refunding star for user {user.id} after failure: {refund_err}")
        
        # Reraise the original exception
        raise e
