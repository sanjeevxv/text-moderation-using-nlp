# from django.db import models
# from users.models import User


# class Content(models.Model):
#     STATUS_CHOICES = (
#         ('safe', 'Safe'),
#         ('flagged', 'Flagged'),
#         ('banned', 'Banned'),
#     )
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contents")
#     text = models.CharField(max_length=1000)
#     created_at = models.DateTimeField(auto_now_add=True)  # use auto_now_add, not auto_now
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='safe')

#     def __str__(self):
#         return f"{self.user.username}: {self.text[:30]}..."


# class ModerationResult(models.Model):
#     LABEL_CHOICES = (
#         ("toxic", "Toxic"),
#         ("spam", "Spam"),
#         ("fraud", "Fraud"),
#         ("drug", "Drug-related"),
#         ("harassment", "Harassment"),
#         ("safe", "Safe"),
#     )
#     content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name="moderation_results")
#     label = models.CharField(choices=LABEL_CHOICES, max_length=20)
#     confidence_score = models.FloatField(default=0.0)
#     action = models.CharField(max_length=20, choices=(("allow", "Allow"), ("review", "Review"), ("ban", "Ban")), default="review")

#     # Additional probability scores
#     spam_score = models.FloatField(default=0.0)
#     ham_score = models.FloatField(default=0.0)
#     phishing_score = models.FloatField(default=0.0)
#     legitimate_score = models.FloatField(default=0.0)
#     drug_score = models.FloatField(default=0.0)
#     toxic_score = models.FloatField(default=0.0)
#     non_toxic_score = models.FloatField(default=0.0)
#     safe_score = models.FloatField(default=0.0)

#     def __str__(self):
#         return f"{self.label} ({self.confidence_score})"


# class Feedback(models.Model):
#     moderator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="feedbacks")
#     moderation_result = models.ForeignKey(ModerationResult, on_delete=models.CASCADE, related_name="feedbacks")
#     decision = models.CharField(max_length=20, choices=(("correct", "Correct"), ("wrong", "Wrong")))
#     moderator_notes = models.TextField(blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Feedback by {self.moderator.username} on {self.moderation_result.label}"


# class SlangWord(models.Model):
#     """Model to store restricted words that should be blocked in content."""
#     word = models.CharField(max_length=100, unique=True)
#     added_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="added_slang_words")
#     created_at = models.DateTimeField(auto_now_add=True)
#     is_active = models.BooleanField(default=True)

#     class Meta:
#         ordering = ['-created_at']
#         verbose_name = 'Restricted Word'
#         verbose_name_plural = 'Restricted Words'

#     def __str__(self):
#         return f"{self.word} (added by {self.added_by.username})"

#     def save(self, *args, **kwargs):
#         # Convert word to lowercase before saving
#         self.word = self.word.lower().strip()
#         super().save(*args, **kwargs)
from django.db import models
from users.models import User
import uuid


# ============================================================
#   CONTENT — Read-only ORM wrapper for Supabase table
# ============================================================
class Content(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="contents"
    )

    text = models.TextField()
    created_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="safe")

    class Meta:
        managed = False               # Django will NOT create/update/delete this table
        db_table = "contents"         # Matches Supabase table

    def __str__(self):
        return f"{self.text[:30]}..."


# ============================================================
#   MODERATION RESULTS — Read-only ORM wrapper for Supabase
# ============================================================
class ModerationResult(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    content = models.ForeignKey(
        Content, on_delete=models.SET_NULL, null=True, blank=True, related_name="moderation_results"
    )

    label = models.CharField(max_length=20)
    confidence_score = models.FloatField(default=0.0)
    action = models.CharField(max_length=20, default="review")

    # Probability scores
    spam_score = models.FloatField(default=0.0)
    ham_score = models.FloatField(default=0.0)
    phishing_score = models.FloatField(default=0.0)
    legitimate_score = models.FloatField(default=0.0)
    drug_score = models.FloatField(default=0.0)
    toxic_score = models.FloatField(default=0.0)
    non_toxic_score = models.FloatField(default=0.0)
    safe_score = models.FloatField(default=0.0)

    # Supabase JSONB → Django JSONField
    reasons = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "moderation_results"

    def __str__(self):
        return f"{self.label} ({self.confidence_score})"


# ============================================================
#   FEEDBACK — Read-only Supabase wrapper
# ============================================================
class Feedback(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)

    moderator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="feedbacks"
    )
    moderation_result = models.ForeignKey(
        ModerationResult, on_delete=models.CASCADE, related_name="feedbacks"
    )

    decision = models.CharField(max_length=20)
    moderator_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "feedbacks"

    def __str__(self):
        return f"Feedback {self.id}"


# ============================================================
#   SLANG WORDS — Read-only Supabase wrapper
# ============================================================
class SlangWord(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)

    word = models.CharField(max_length=100)
    added_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="added_slang_words"
    )
    created_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "slang_words"
        ordering = ["-created_at"]

    def __str__(self):
        return self.word.lower()
