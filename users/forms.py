from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, BanHistory


# -------------------------------
# Registration Form
# -------------------------------
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "role")  # password1 + password2 included automatically


# -------------------------------
# Login Form (Simple Form)
# -------------------------------
class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your email"
        })
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your password"
        })
    )


# -------------------------------
# Ban / Unban Forms
# -------------------------------
class BanUserForm(forms.ModelForm):
    class Meta:
        model = BanHistory
        fields = ["reason", "start_date", "end_date"]


class UnbanUserForm(forms.Form):
    user_id = forms.IntegerField(widget=forms.HiddenInput())
