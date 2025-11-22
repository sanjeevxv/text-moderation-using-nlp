# dashboard/views.py

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime
from dateutil import parser            # ✅ BEST timestamp parser

from .forms import AuditLogFilterForm
from safenet.supabase_client import supabase

from moderation.forms import ContentForm, SlangWordForm
from pytz import timezone

# Timezones
UTC = timezone("UTC")
IST = timezone("Asia/Kolkata")

logger = logging.getLogger(__name__)


# =====================================================================
#                           DASHBOARD HOME
# =====================================================================
@login_required
def dashboard_home(request):
    from moderation.views import _row_to_content_obj

    try:
        # ===== Basic Stats =====
        total_content = (
            supabase.table("contents")
            .select("id", count="exact")
            .execute()
            .count
        ) or 0

        flagged_content = (
            supabase.table("contents")
            .select("id", count="exact")
            .eq("status", "flagged")
            .execute()
            .count
        ) or 0

        banned_users = (
            supabase.table("profiles")
            .select("id", count="exact")
            .eq("is_banned", True)
            .execute()
            .count
        ) or 0

        # ===== Recent Comments =====
        recent_rows = (
            supabase.table("contents")
            .select("*")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
            .data
        ) or []

        recent_comments = []

        for r in recent_rows:

            # Convert created_at → IST (100% reliable)
            raw_ts = r.get("created_at")
            r["created_at_ist"] = convert_to_ist(raw_ts)

            # if raw_ts:
            #     try:
            #         dt = parser.isoparse(raw_ts)      # ✅ parse ANY Supabase timestamp
            #         r["created_at_ist"] = dt.astimezone(IST)
            #     except:
            #         r["created_at_ist"] = None
            # else:
            #     r["created_at_ist"] = None

            # Fetch profile
            profile_row = None
            if r.get("user_id"):
                p = (
                    supabase.table("profiles")
                    .select("id, username, email")
                    .eq("id", r["user_id"])
                    .single()
                    .execute()
                )
                profile_row = p.data if p.data else None

            # Fetch moderation results
            mr = (
                supabase.table("moderation_results")
                .select("*")
                .eq("content_id", r["id"])
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            latest_mod = mr.data[0] if mr.data else None

            # Convert row → object
            obj = _row_to_content_obj(r, profile_row, latest_mod)

            # IMPORTANT: Pass created_at_ist to object
            obj.created_at_ist = r.get("created_at_ist")

            recent_comments.append(obj)

        # Restricted Words
        slang_words = (
            supabase.table("slang_words")
            .select("*")
            .order("created_at", desc=True)
            .limit(15)
            .execute()
            .data
        )

    except Exception as e:
        logger.error("Dashboard load failed: %s", str(e))
        total_content = flagged_content = banned_users = 0
        recent_comments = slang_words = []
        messages.error(request, "Failed to load dashboard data.")

    return render(
        request,
        "dashboard/home.html",
        {
            "form": ContentForm(),
            "slang_form": SlangWordForm(),
            "slang_words": slang_words,
            "stats": {
                "total_content": total_content,
                "flagged_content": flagged_content,
                "banned_users": banned_users,
            },
            "recent_comments": recent_comments,
        },
    )


# =====================================================================
#                           AUDIT LOGS PAGE
# =====================================================================
@login_required
def audit_logs_view(request):

    form = AuditLogFilterForm(request.GET or None)

    # Joined lookup
    query = supabase.table("audit_logs").select("""
        *,
        user:user_id (id, username, email),
        content:content_id (id, text, created_at),
        moderation_result:moderation_result_id (id, label, reasons)
    """)

    # Filters
    if form.is_valid():
        action = form.cleaned_data.get("action")
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")

        if action:
            query = query.eq("action", action)
        if start_date:
            query = query.gte("timestamp", f"{start_date} 00:00:00")
        if end_date:
            query = query.lte("timestamp", f"{end_date} 23:59:59")

    # Fetch logs
    try:
        logs = query.order("timestamp", desc=True).execute().data or []
    except Exception as e:
        print("Supabase error:", e)
        logs = []

    # Timestamp conversion → IST
    for log in logs:
        raw_ts = log.get("timestamp")
        log["timestamp_ist"] = convert_to_ist(raw_ts)


        # if raw_ts:
        #     try:
        #         dt = parser.isoparse(raw_ts)
        #         log["timestamp_ist"] = dt.astimezone(IST)
        #     except:
        #         log["timestamp_ist"] = None
        # else:
        #     log["timestamp_ist"] = None

        # Content timestamp → IST

        if log.get("content") and log["content"].get("created_at"):
            try:
                ct = log["content"].get("created_at")
                log["content"]["created_at_ist"] = convert_to_ist(ct)
            except:
                log["content"]["created_at_ist"] = None
        else:
            log["content"]["created_at_ist"] = None

    return render(
        request,
        "dashboard/audit_logs.html",
        {"logs": logs, "form": form},
    )


# =====================================================================
#                            MANAGE USERS
# =====================================================================
@login_required
def manage_users_view(request):

    if request.user.role != "admin":
        messages.error(request, "You don't have permission to manage users.")
        return redirect("dashboard_home")

    try:
        users = (
            supabase.table("profiles")
            .select("*")
            .order("created_at", desc=True)
            .execute()
            .data
        )
    except Exception:
        users = []
        messages.error(request, "Failed to load users.")

    return render(request, "dashboard/manage_users.html", {"users": users})


# =====================================================================
#                       BAN / UNBAN USER (ADMIN)
# =====================================================================
@login_required
def toggle_user_ban_view(request, user_id):

    if request.user.role != "admin":
        messages.error(request, "You don't have permission to ban users.")
        return redirect("dashboard_home")

    user_data = (
        supabase.table("profiles")
        .select("*")
        .eq("id", user_id)
        .single()
        .execute()
    )

    if user_data.error:
        messages.error(request, "User not found.")
        return redirect("manage_users")

    target_user = user_data.data

    if request.method == "POST":
        action = request.POST.get("action")
        reason = request.POST.get("reason", "")

        if action == "ban":
            supabase.table("profiles").update({"is_banned": True}).eq("id", user_id).execute()
            messages.warning(request, f"{target_user['username']} has been banned.")

            supabase.table("audit_logs").insert({
                "user_id": request.user.supabase_id,
                "action": "banned_user",
                "notes": f"Banned {target_user['username']}: {reason}"
            }).execute()

        elif action == "unban":
            supabase.table("profiles").update({"is_banned": False}).eq("id", user_id).execute()
            messages.success(request, f"{target_user['username']} has been unbanned.")

            supabase.table("audit_logs").insert({
                "user_id": request.user.supabase_id,
                "action": "unbanned_user",
                "notes": f"Unbanned {target_user['username']}: {reason}"
            }).execute()

        return redirect("manage_users")

    return render(request, "dashboard/toggle_user_ban.html", {"target_user": target_user})

def convert_to_ist(raw_ts):
    if not raw_ts:
        return None

    try:
        dt = parser.isoparse(raw_ts)
    except:
        return None

    # If timestamp has NO timezone → force UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    # Convert UTC → IST
    return dt.astimezone(IST)
