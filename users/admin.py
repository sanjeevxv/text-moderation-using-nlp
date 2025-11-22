from django.contrib import admin
from .models import User, BanHistory

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "is_banned", "is_active", "date_joined")
    list_filter = ("role", "is_banned", "is_active")
    search_fields = ("username", "email")

@admin.register(BanHistory)
class BanHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "reason", "start_date", "end_date")
    search_fields = ("user__username", "reason")
