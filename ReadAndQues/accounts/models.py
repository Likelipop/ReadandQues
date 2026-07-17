from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar_url = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        default="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=256&h=256"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Statistics / Analytics
    total_articles_imported = models.PositiveIntegerField(default=0)
    total_questions_solved = models.PositiveIntegerField(default=0)
    correct_answers_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Profile of {self.user.username}"


# Signal to automatically create/save UserProfile when a User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Ensure profile exists for backwards compatibility/existing users in testing
    if not hasattr(instance, "profile"):
        UserProfile.objects.create(user=instance)
    instance.profile.save()
