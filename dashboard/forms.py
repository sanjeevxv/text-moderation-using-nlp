from django import forms


# ✅ Form to filter audit logs
class AuditLogFilterForm(forms.Form):
    ACTION_CHOICES = [
        ("", "All"),
        ("reviewed", "Reviewed Content"),
        ("banned_user", "Banned User"),
        ("unbanned_user", "Unbanned User"),
        ("updated_status", "Updated Content Status"),
        ("feedback_given", "Feedback Given"),
    ]

    action = forms.ChoiceField(choices=ACTION_CHOICES, required=False)
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
