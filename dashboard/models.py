# from django.db import models
# from users.models import User
# from moderation.models import Content, ModerationResult


# class AuditLog(models.Model):
#     ACTION_CHOICES = (
#         ("reviewed", "Reviewed Content"),
#         ("banned_user", "Banned User"),
#         ("unbanned_user", "Unbanned User"),
#         ("updated_status", "Updated Content Status"),
#         ("feedback_given", "Feedback Given"),
#     )

#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="audit_logs")  # moderator/admin who did action
#     action = models.CharField(max_length=50, choices=ACTION_CHOICES)
#     content = models.ForeignKey(Content, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
#     moderation_result = models.ForeignKey(ModerationResult, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
#     timestamp = models.DateTimeField(auto_now_add=True)
#     notes = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return f"{self.user.username} - {self.action} at {self.timestamp}"

# dashboard/models.py
from django.db import models

class AuditLog(models.Model):
    user_id = models.CharField(max_length=255)  # Supabase UUID
    action = models.CharField(max_length=50)
    content_id = models.CharField(max_length=255, null=True, blank=True)
    moderation_result_id = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField()
    notes = models.TextField(null=True, blank=True)

    class Meta:
        managed = False   # 🚨 IMPORTANT
        db_table = "audit_logs"  # Supabase table name

