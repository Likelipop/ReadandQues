from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar_url = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        default="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=256&h=256",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Star System
    stars = models.PositiveIntegerField(default=10)

    # Statistics / Analytics
    total_articles_imported = models.PositiveIntegerField(default=0)
    total_questions_solved = models.PositiveIntegerField(default=0)
    correct_answers_count = models.PositiveIntegerField(default=0)
    avg_incorrect_questions = models.FloatField(default=0.0)
    avg_time_spent = models.FloatField(default=0.0)
    last_test_date = models.DateField(blank=True, null=True)
    streak = models.PositiveIntegerField(default=0)
    total_tests_completed = models.PositiveIntegerField(default=0)

    # Login Day Tracking
    last_login_date = models.DateField(blank=True, null=True)
    login_days_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Profile of {self.user.username}"


# Signal to automatically create/save UserProfile when a User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        from django.conf import settings

        default_stars = 100 if settings.DEBUG else 10
        UserProfile.objects.create(user=instance, stars=default_stars)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Ensure profile exists for backwards compatibility/existing users in testing
    if not hasattr(instance, "profile"):
        from django.conf import settings

        default_stars = 100 if settings.DEBUG else 10
        UserProfile.objects.create(user=instance, stars=default_stars)


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    # Get or create profile
    profile, created = UserProfile.objects.get_or_create(user=user)

    from django.utils import timezone

    today = timezone.now().date()

    if profile.last_login_date != today:
        profile.login_days_count += 1
        profile.last_login_date = today
        profile.save()


class EmailVerification(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="verification"
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        from django.utils import timezone

        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Verification code {self.code} for {self.user.email}"
