from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "total_articles_imported", "total_questions_solved", "created_at")
    search_fields = ("user__username", "user__email")
