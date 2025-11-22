import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import CustomUserCreationForm, LoginForm
from .models import User
from safenet.supabase_client import supabase, supabase_anon
from django.contrib.auth.hashers import make_password, check_password

logger = logging.getLogger(__name__)


# ===========================================
#             REGISTER VIEW
# ===========================================
import logging
import uuid
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.hashers import make_password

from .forms import CustomUserCreationForm
from .models import User
from safenet.supabase_client import supabase

logger = logging.getLogger(__name__)

def register_view(request):

    if request.user.is_authenticated:
        return redirect("dashboard_home")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():

            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password1"]
            role = form.cleaned_data["role"]

            # Hash password once using Django hasher
            hashed_password = make_password(password)
            supabase_uid = str(uuid.uuid4())

            try:
                # 1️⃣ Check if email exists in Supabase
                existing = supabase.table("profiles").select("id") \
                    .eq("email", email).execute()
                
                if existing.data:
                    messages.error(request, "Email already exists!")
                    return render(request, "users/register.html", {"form": form})

                # 2️⃣ Insert into Supabase
                res = supabase.table("profiles").insert({
                    "id": supabase_uid,
                    "email": email,
                    "username": username,
                    "password": hashed_password,  # store Django-style hash
                    "role": role,
                    "is_banned": False
                }).execute()

                # 3️⃣ Create Django user with SAME password hash
                user = User(
                    username=username,
                    email=email,
                    supabase_id=supabase_uid,
                    role=role,
                    is_banned=False,
                    password=hashed_password  # IMPORTANT!
                )
                user.save()

                login(request, user)
                messages.success(request, "Account created successfully!")
                return redirect("dashboard_home")

            except Exception as e:
                logger.error(f"Register error: {e}", exc_info=True)
                messages.error(request, f"Registration failed: {e}")
                return redirect("register")

        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{field.title()}: {err}")

    else:
        form = CustomUserCreationForm()

    return render(request, "users/register.html", {"form": form})


# ===========================================
#               LOGIN VIEW
# ===========================================
def login_view(request):

    if request.user.is_authenticated:
        return redirect("dashboard_home")

    form = LoginForm(request.POST or None)

    if request.method == "POST":

        if not form.is_valid():
            messages.error(request, "Fill all fields")
            return render(request, "users/login.html", {"form": form})

        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]

        # Fetch from Supabase
        result = supabase.table("profiles") \
                         .select("*") \
                         .eq("email", email) \
                         .single() \
                         .execute()

        if not result.data:
            messages.error(request, "Invalid email or password")
            return render(request, "users/login.html", {"form": form})

        profile = result.data  # dict
        supabase_id = profile["id"]

        # Validate password (Django hash stored in Supabase)
        if not check_password(password, profile["password"]):
            messages.error(request, "Invalid email or password")
            return render(request, "users/login.html", {"form": form})

        # BAN check
        if profile.get("is_banned"):
            messages.error(request, "Your account is banned.")
            return render(request, "users/login.html", {"form": form})

        # -----------------------------
        # 🔥 FIND LOCAL DJANGO USER
        # -----------------------------
        user = User.objects.filter(supabase_id=supabase_id).first()

        if not user:
            # fallback: match by email
            user = User.objects.filter(email=email).first()

        if not user:
            # create fresh Django user (first-time login)
            user = User.objects.create(
                username=profile["username"],
                email=profile["email"],
                supabase_id=supabase_id,
                role=profile["role"],
                is_banned=profile["is_banned"],
                password=profile["password"],  # same hashed pw
            )
        else:
            # -----------------------------
            # 🔥 ALWAYS SYNC EVERY LOGIN
            # -----------------------------
            updated = False

            if user.supabase_id != supabase_id:
                user.supabase_id = supabase_id
                updated = True

            if user.role != profile["role"]:
                user.role = profile["role"]
                updated = True

            if user.is_banned != profile["is_banned"]:
                user.is_banned = profile["is_banned"]
                updated = True

            if updated:
                user.save()

        # LOGIN
        login(request, user)
        messages.success(request, f"Welcome back {user.username}!")
        return redirect("dashboard_home")

    return render(request, "users/login.html", {"form": form})

# ===========================================
#                 LOGOUT
# ===========================================
@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


# ===========================================
#             BANNED USERS
# ===========================================
@login_required
def banned_users_view(request):
    banned_users = User.objects.filter(is_banned=True)
    return render(request, "users/banned_users.html", {"banned_users": banned_users})
