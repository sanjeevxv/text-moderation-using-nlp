# from django.db import models
# from django.contrib.auth.models import AbstractUser


# # Custom User Model (extends Django User)
# class User(AbstractUser):
#     ROLE_CHOICES = (
#         ('admin', 'Admin'),
#         ('moderator', 'Moderator'),
#         ('user', 'User'),
#     )
#     role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
#     is_banned = models.BooleanField(default=False)

#     def __str__(self):
#         return self.username


# class BanHistory(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ban_history")
#     reason = models.CharField(max_length=200)
#     start_date = models.DateField()
#     end_date = models.DateField(null=True, blank=True)  # blank = temporary bans allowed

#     def __str__(self):
#         return f"{self.user.username} banned for {self.reason}"

from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('user', 'User'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    is_banned = models.BooleanField(default=False)

    # LINK TO SUPABASE PROFILE
    supabase_id = models.CharField(max_length=255, unique=True, null=True, blank=True)


    def __str__(self):
        return self.username

class BanHistory(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ban_history"
    )

    reason = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} banned for {self.reason}"
