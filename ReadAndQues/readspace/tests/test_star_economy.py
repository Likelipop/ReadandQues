from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from readspace.utils import StarDeductionError, consume_user_star


class StarEconomyTestSuite(TestCase):
    """Gamification Star Economy & Atomic Balance Validation."""

    def setUp(self):
        self.user = User.objects.create_user(username="star_tester", email="star@example.com", password="TestPass123!")
        self.profile = UserProfile.objects.get(user=self.user)
        self.profile.stars = 3
        self.profile.save()

    def test_star_deduction_and_context_manager(self):
        """Verify consume_user_star safely decrements star balance."""
        initial_stars = self.profile.stars
        with consume_user_star(self.user):
            pass

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.stars, initial_stars - 1)

    def test_star_refund_on_failure(self):
        """Verify star is refunded if an unhandled error occurs in the operation block."""
        initial_stars = self.profile.stars
        try:
            with consume_user_star(self.user):
                raise RuntimeError("Simulated pipeline crash")
        except RuntimeError:
            pass

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.stars, initial_stars)

    def test_insufficient_stars_raises_exception(self):
        """Verify user with 0 stars cannot perform star-consuming operations."""
        self.profile.stars = 0
        self.profile.save()

        with self.assertRaises(StarDeductionError):
            with consume_user_star(self.user):
                pass
