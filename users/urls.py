from django.urls import path
from .views import register_view, login_view, logout_view, banned_users_view

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('banned/', banned_users_view, name='banned_users'),
]


