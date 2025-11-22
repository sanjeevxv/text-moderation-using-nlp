from django.urls import path
from .views import dashboard_home, audit_logs_view, manage_users_view, toggle_user_ban_view

urlpatterns = [
    path('', dashboard_home, name='dashboard_home'),
    path('logs/', audit_logs_view, name='audit_logs'),
    path('users/', manage_users_view, name='manage_users'),
    path('users/<int:user_id>/ban/', toggle_user_ban_view, name='toggle_user_ban'),
]


