from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from bson import ObjectId
from articles.utils.db import article_collection, insert_article_document


class ArticlesViewsAndDbTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username="user1", email="u1@example.com", password="password123")
        self.user2 = User.objects.create_user(username="user2", email="u2@example.com", password="password123")
        
        # Insert test articles in Mongo
        self.article_ids = []
        
        # 1. Completed article by user1
        self.art_completed_u1 = {
            "url": "https://vietnamnews.vn/article-completed-u1",
            "title": "Completed U1 Test",
            "original_text": "Sample text for completed u1",
            "status": "completed",
            "user_id": self.user1.id,
            "exams": [{"quizzes": []}]
        }
        self.id_completed_u1 = insert_article_document(self.art_completed_u1)
        self.article_ids.append(self.id_completed_u1)

        # 2. Pending article by user1
        self.art_pending_u1 = {
            "url": "https://vietnamnews.vn/article-pending-u1",
            "title": "Pending U1 Test",
            "original_text": "Sample text for pending u1",
            "status": "pending",
            "user_id": self.user1.id
        }
        self.id_pending_u1 = insert_article_document(self.art_pending_u1)
        self.article_ids.append(self.id_pending_u1)

    def tearDown(self):
        # Clean up test documents in Mongo
        for aid in self.article_ids:
            article_collection.delete_one({"_id": ObjectId(aid)})

    def test_get_completed_articles_db_helper(self):
        """Verify get_completed_articles returns completed articles only."""
        from articles.utils.db import get_completed_articles
        completed = get_completed_articles()
        # Should contain at least our completed test article
        ids = [doc["id"] for doc in completed]
        self.assertIn(self.id_completed_u1, ids)
        self.assertNotIn(self.id_pending_u1, ids)

    def test_all_tests_view_public(self):
        """Verify anyone can view the All Tests page without logging in."""
        response = self.client.get(reverse("all_tests"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Completed U1 Test")
        self.assertNotContains(response, "Pending U1 Test")

    def test_practice_completed_article_other_user(self):
        """Verify that user2 can practice (view detail) user1's completed article."""
        self.client.force_login(self.user2)
        response = self.client.get(reverse("article_detail", args=[self.id_completed_u1]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Completed U1 Test")

    def test_practice_pending_article_other_user_denied(self):
        """Verify that user2 cannot view user1's pending article."""
        self.client.force_login(self.user2)
        response = self.client.get(reverse("article_detail", args=[self.id_pending_u1]))
        self.assertEqual(response.status_code, 302) # Redirect to home
        self.assertRedirects(response, reverse("home"))

    def test_practice_article_guest_redirects_to_login(self):
        """Verify that guest users are redirected to login when trying to practice."""
        response = self.client.get(reverse("article_detail", args=[self.id_completed_u1]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue("login" in response.url)
