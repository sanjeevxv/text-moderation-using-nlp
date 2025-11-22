from django import forms
from .models import Content, Feedback, SlangWord


# ✅ Form for users to post comments
class ContentForm(forms.ModelForm):
    class Meta:
        model = Content
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Write your comment here...",
                    "class": "form-control",
                }
            )
        }


# Form for moderators to give feedback
class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["decision", "moderator_notes"]
        widgets = {
            "decision": forms.RadioSelect(choices=[("correct", "Correct"), ("wrong", "Wrong")]),
            "moderator_notes": forms.Textarea(attrs={
                "rows": 3,
                "class": "form-control",
                "placeholder": "Add any additional notes..."
            })
        }


class SlangWordForm(forms.Form):
    WORD_ACTIONS = [
        ('add', 'Add Word'),
        ('delete', 'Delete Word'),
    ]
    
    word = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter a word to add/remove',
            'required': 'required',
            'autocomplete': 'off'
        })
    )
    
    action = forms.ChoiceField(
        choices=WORD_ACTIONS,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'style': 'max-width: 150px;',
            'required': 'required'
        })
    )
