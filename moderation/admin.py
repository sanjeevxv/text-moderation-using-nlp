from django.contrib import admin
from .models import Content, ModerationResult, Feedback

@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ("user", "text", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "text")

@admin.register(ModerationResult)
class ModerationResultAdmin(admin.ModelAdmin):
    list_display = ("content", "label", "confidence_score", "action")
    list_filter = ("label", "action")
    search_fields = ("content__text",)

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("moderator", "moderation_result", "decision", "created_at")
    list_filter = ("decision", "created_at")
    search_fields = ("moderator__username", "notes")
