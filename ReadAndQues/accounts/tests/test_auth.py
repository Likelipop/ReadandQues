"""
Unit tests for user authentication, registration, and profile views.
"""

from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class AccountsAuthTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="john_doe",
            email="john@example.com",
            password="securepassword123",
        )
        self.profile = self.user.profile

    def test_login_page_renders(self):
        with patch("service.selectors.get_hot_news", return_value=[]):
            response = self.client.get(reverse("login"))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Login")

    def test_login_successful_with_username(self):
        with patch("service.selectors.get_hot_news", return_value=[]):
            response = self.client.post(
                reverse("login"),
                {"username": "john_doe", "password": "securepassword123"},
            )
            self.assertEqual(response.status_code, 302)

    def test_login_successful_with_email(self):
        with patch("service.selectors.get_hot_news", return_value=[]):
            response = self.client.post(
                reverse("login"),
                {"username": "john@example.com", "password": "securepassword123"},
            )
            self.assertEqual(response.status_code, 302)

    def test_logout_view(self):
        self.client.login(username="john_doe", password="securepassword123")
        with patch("service.selectors.get_hot_news", return_value=[]):
            response = self.client.get(reverse("logout"))
            self.assertEqual(response.status_code, 302)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_profile_accessible_when_logged_in(self):
        self.client.login(username="john_doe", password="securepassword123")
        with patch("service.selectors.get_hot_news", return_value=[]):
            response = self.client.get(reverse("profile"))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "john_doe")
