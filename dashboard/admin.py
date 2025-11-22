# from django.contrib import admin
# from .models import AuditLog

# @admin.register(AuditLog)
# class AuditLogAdmin(admin.ModelAdmin):
#     list_display = ("user", "action", "content", "moderation_result", "timestamp")
#     list_filter = ("action", "timestamp")
#     search_fields = ("user__username", "notes")

# dashboard/admin.py
# dashboard/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.timezone import localtime

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin for AuditLog — defensive display functions to avoid E108 errors."""

    list_display = (
        "id",
        "user_display",
        "action",
        "content_display",
        "moderation_result_display",
        "timestamp_display",
    )
    list_filter = ("action",)
    search_fields = ("notes",)

    # show newer items first
    ordering = ("-timestamp",)

    # ---------- Display helpers ----------
    def user_display(self, obj):
        """
        Try multiple ways to show user:
        - obj.user.username (if FK present)
        - obj.user (stringified)
        - obj.user_id (if present)
        """
        # FK object present
        user = getattr(obj, "user", None)
        if user:
            # If user is a model instance with username
            username = getattr(user, "username", None)
            if username:
                return username
            return str(user)

        # fallback to a raw user id field (common in shadow models)
        uid = getattr(obj, "user_id", None) or getattr(obj, "user_id", None)
        return str(uid) if uid else "—"
    user_display.short_description = "User"
    user_display.admin_order_field = "user"  # may be ignored if not a real field

    def content_display(self, obj):
        """
        Show snippet of content:
        - obj.content.text (if FK present)
        - obj.content (stringified)
        - obj.content_id (raw id)
        """
        content = getattr(obj, "content", None)
        if content:
            text = getattr(content, "text", None)
            if text:
                snippet = text if len(text) <= 80 else text[:77] + "..."
                return snippet
            return str(content)

        cid = getattr(obj, "content_id", None)
        return str(cid) if cid else "—"
    content_display.short_description = "Content"

    def moderation_result_display(self, obj):
        """
        Show the moderation result label + score where possible.
        - obj.moderation_result.label/confidence_score
        - obj.moderation_result (string)
        - obj.moderation_result_id (raw id)
        """
        mr = getattr(obj, "moderation_result", None)
        if mr:
            label = getattr(mr, "label", None)
            score = getattr(mr, "confidence_score", None)
            if label and score is not None:
                try:
                    return f"{label} ({float(score):.2f})"
                except Exception:
                    return f"{label} ({score})"
            if label:
                return label
            return str(mr)

        mrid = getattr(obj, "moderation_result_id", None)
        return str(mrid) if mrid else "—"
    moderation_result_display.short_description = "Moderation Result"

    def timestamp_display(self, obj):
        """Format timestamp nicely and safely."""
        ts = getattr(obj, "timestamp", None)
        if not ts:
            return "—"
        try:
            # convert to local timezone and format succinctly
            local = localtime(ts)
            return local.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(ts)
    timestamp_display.short_description = "Time"
    timestamp_display.admin_order_field = "timestamp"

    # Optionally make some fields read-only in admin detail view
    readonly_fields = ("user_display", "action", "content_display", "moderation_result_display", "timestamp_display")

    # Improve list page performance by not attempting to prefetch unrelated relations blindly
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Try to select_related if FK fields exist to reduce queries (safe-guarded)
        try:
            # If model has real FK attributes, select_related them
            if "user" in [f.name for f in self.model._meta.fields]:
                qs = qs.select_related("user")
            if "content" in [f.name for f in self.model._meta.fields]:
                qs = qs.select_related("content")
            if "moderation_result" in [f.name for f in self.model._meta.fields]:
                qs = qs.select_related("moderation_result")
        except Exception:
            # If any introspection fails, just return qs
            pass
        return qs

