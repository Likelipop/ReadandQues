import datetime
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import EmailVerification


class AccountsAuthTests(TestCase):
    def setUp(self):
        self.client = Client()

    def bypass_rate_limit(self):
        session = self.client.session
        session["last_submit_at"] = 0.0
        session.save()

    def test_dual_login(self):
        """Verify that users can log in using either their username or email."""
        # Create an active test user
        user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
        user.is_active = True
        user.save()

        # 1. Login with username
        self.bypass_rate_limit()
        response = self.client.post(reverse("login"), {
            "username": "testuser",
            "password": "password123"
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"))

        # Logout
        self.client.logout()

        # 2. Login with email
        self.bypass_rate_limit()
        response = self.client.post(reverse("login"), {
            "username": "test@example.com",
            "password": "password123"
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"))

    def test_registration_flow_and_activation(self):
        """Verify that registration creates an inactive user and correct code activates the user."""
        response = self.client.post(reverse("register"), {
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "confirm_password": "password123"
        })
        # Should redirect to verify email page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("verify_email"))

        # Verify user was created in DB but is inactive
        user = User.objects.get(username="newuser")
        self.assertFalse(user.is_active)

        # Verify EmailVerification code exists
        verification = EmailVerification.objects.get(user=user)
        self.assertEqual(len(verification.code), 6)
        self.assertTrue(verification.code.isdigit())

        # Submit the correct verification code
        self.bypass_rate_limit()
        response = self.client.post(reverse("verify_email"), {
            "code": verification.code
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"))

        # Verify user is now active
        user.refresh_from_db()
        self.assertTrue(user.is_active)

        # Verify verification code is deleted
        with self.assertRaises(EmailVerification.DoesNotExist):
            EmailVerification.objects.get(user=user)

    def test_verification_errors(self):
        """Verify handling of incorrect and expired verification codes."""
        # Create inactive user and verification record
        user = User.objects.create_user(username="inactiveuser", email="inactive@example.com", password="password123")
        user.is_active = False
        user.save()

        verification = EmailVerification.objects.create(
            user=user,
            code="123456",
            expires_at=timezone.now() + datetime.timedelta(minutes=5)
        )

        # Set session to simulate completed registration form
        session = self.client.session
        session["verification_user_id"] = user.id
        session.save()

        # 1. Post incorrect code
        self.bypass_rate_limit()
        response = self.client.post(reverse("verify_email"), {
            "code": "654321"
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mã xác thực không chính xác.")
        user.refresh_from_db()
        self.assertFalse(user.is_active)

        # 2. Post expired code
        verification.expires_at = timezone.now() - datetime.timedelta(seconds=1)
        verification.save()

        self.bypass_rate_limit()
        response = self.client.post(reverse("verify_email"), {
            "code": "123456"
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mã xác thực đã hết hạn.")
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_resend_cooldown_rate_limit(self):
        """Verify that resending verification code is rate limited to 60 seconds."""
        user = User.objects.create_user(username="resenduser", email="resend@example.com", password="password123")
        user.is_active = False
        user.save()

        verification = EmailVerification.objects.create(
            user=user,
            code="111111",
            expires_at=timezone.now() + datetime.timedelta(minutes=5)
        )

        session = self.client.session
        session["verification_user_id"] = user.id
        session.save()

        # 1. First resend attempt immediately (within 60s) -> should be blocked by cooldown
        response = self.client.get(reverse("resend_verification"), follow=True)
        self.assertContains(response, "giây trước khi gửi lại mã.")

        # 2. Backdate created_at of verification record in DB by 61 seconds
        verification.created_at = timezone.now() - datetime.timedelta(seconds=61)
        verification.save()

        # Second resend attempt -> should succeed
        response = self.client.get(reverse("resend_verification"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("verify_email"))

        # Verify new code is generated
        verification.refresh_from_db()
        self.assertNotEqual(verification.code, "111111")
        self.assertEqual(len(verification.code), 6)

    def test_overwrite_inactive_registration(self):
        """Verify that registering with a duplicate username or email that is inactive overwrites it."""
        # Register user first time
        self.bypass_rate_limit()
        self.client.post(reverse("register"), {
            "username": "overlapuser",
            "email": "overlap@example.com",
            "password": "password123",
            "confirm_password": "password123"
        })

        # Register same username and email a second time with a different password
        self.bypass_rate_limit()
        response = self.client.post(reverse("register"), {
            "username": "overlapuser",
            "email": "overlap@example.com",
            "password": "newpassword456",
            "confirm_password": "newpassword456"
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("verify_email"))

        # Verify only one user exists in the database
        users = User.objects.filter(username="overlapuser")
        self.assertEqual(users.count(), 1)
        
        user = users.first()
        self.assertFalse(user.is_active)
        self.assertEqual(user.email, "overlap@example.com")

        # Verify password was updated (should be able to check password)
        self.assertTrue(user.check_password("newpassword456"))


class ProfileAndStarsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
        self.user.is_active = True
        self.user.save()
        self.client.force_login(self.user)

    @override_settings(DEBUG=True)
    def test_default_stars_allocation_dev(self):
        """Verify that default star allocation is 100 in dev (settings.DEBUG is True)."""
        dev_user = User.objects.create_user(username="devuser", email="dev@example.com", password="password123")
        self.assertEqual(dev_user.profile.stars, 100)

    def test_default_stars_allocation_prod(self):
        """Verify that default star allocation is 10 in prod (settings.DEBUG is False)."""
        from django.conf import settings
        # Temporarily mock settings.DEBUG to False
        original_debug = settings.DEBUG
        settings.DEBUG = False
        try:
            prod_user = User.objects.create_user(username="produser", email="prod@example.com", password="password123")
            self.assertEqual(prod_user.profile.stars, 10)
        finally:
            settings.DEBUG = original_debug

    def test_login_days_count_increment(self):
        """Verify that login_days_count increments only once per day."""
        profile = self.user.profile
        self.assertEqual(profile.login_days_count, 0)
        
        # Trigger login signal
        from django.contrib.auth.signals import user_logged_in
        user_logged_in.send(sender=User, request=None, user=self.user)
        
        profile.refresh_from_db()
        self.assertEqual(profile.login_days_count, 1)
        
        # Same day login -> should not increment
        user_logged_in.send(sender=User, request=None, user=self.user)
        profile.refresh_from_db()
        self.assertEqual(profile.login_days_count, 1)

    def test_change_password_success(self):
        """Verify that a user can successfully change their password."""
        response = self.client.post(reverse("profile"), {
            "old_password": "password123",
            "new_password1": "newsecurepassword123",
            "new_password2": "newsecurepassword123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("profile"))
        
        # Check password updated
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newsecurepassword123"))

    def test_change_password_mismatch(self):
        """Verify password change fails when new passwords do not match."""
        response = self.client.post(reverse("profile"), {
            "old_password": "password123",
            "new_password1": "newsecurepassword123",
            "new_password2": "newsecurepassword456",
        })
        self.assertEqual(response.status_code, 200) # Form errors displayed
        self.assertContains(response, "Vui lòng sửa các lỗi bên dưới")

        # Verify old password still works
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("password123"))

    def test_article_import_limits_by_stars(self):
        """Verify that user cannot import articles if they have 0 stars."""
        profile = self.user.profile
        profile.stars = 0
        profile.save()

        # Regular post attempt
        response = self.client.post(reverse("import_article"), {
            "url": "https://vietnamnews.vn/economy/123456"
        })
        # Should render import page with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bạn đã hết Star!")

        # Ajax attempt
        response = self.client.post(
            reverse("import_article"),
            {"url": "https://vietnamnews.vn/economy/123456"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json().get("message"), "NO_STARS")

