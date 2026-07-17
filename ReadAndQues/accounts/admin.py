from django.contrib import admin
from .models import UserProfile, EmailVerification

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "total_articles_imported", "total_questions_solved", "created_at")
    search_fields = ("user__username", "user__email")

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "created_at", "expires_at")
    search_fields = ("user__username", "user__email", "code")
