# moderation/views.py
import logging
import json
from types import SimpleNamespace
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .forms import ContentForm, FeedbackForm, SlangWordForm
from .models import ModerationResult  # kept for typing / local read-only model if needed
from dashboard.models import AuditLog as AuditLogModel  # only for naming / not used for writes
from ai_models.drug_embeddings import get_embedding, index as pinecone_index, EMBEDDER

from moderation.engine import predict_all

# Supabase client (must be created in safenet/supabase_client.py)
from safenet.supabase_client import supabase
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)


# ------------------------
# Helpers
# ------------------------
# ------------------------
# Helpers
# ------------------------
def _safe_parse_dt(value):
    """Safely parse timestamps from Supabase."""
    if not value:
        return None
    dt = parse_datetime(value)
    return dt or None


def _row_to_profile(row):
    if not row:
        return SimpleNamespace(id=None, username="Unknown", email=None)
    return SimpleNamespace(
        id=row.get("id"),
        username=row.get("username") or row.get("email") or "Unknown",
        email=row.get("email"),
    )


def _row_to_content_obj(row, profile_row=None, latest_mod_row=None):
    user_obj = _row_to_profile(profile_row) if profile_row else SimpleNamespace(
        id=row.get("user_id"), username="Unknown"
    )

    moderation_results = []
    if latest_mod_row:
        mr = SimpleNamespace(
            id=latest_mod_row.get("id"),
            label=latest_mod_row.get("label"),
            confidence_score=latest_mod_row.get("confidence_score"),
            spam_score=latest_mod_row.get("spam_score") or 0.0,
            phishing_score=latest_mod_row.get("phishing_score") or 0.0,
            toxic_score=latest_mod_row.get("toxic_score") or 0.0,
            drug_score=latest_mod_row.get("drug_score") or 0.0,
            safe_score=latest_mod_row.get("safe_score") or 0.0,
            reasons=latest_mod_row.get("reasons") or [],
            created_at=_safe_parse_dt(latest_mod_row.get("created_at")),
        )
        moderation_results.append(mr)

    return SimpleNamespace(
        id=row.get("id"),
        user=user_obj,
        user_id=row.get("user_id"),
        text=row.get("text"),
        created_at=_safe_parse_dt(row.get("created_at")),
        status=row.get("status"),
        moderation_results=moderation_results
    )


def get_user_supabase_id(user):
    """
    Return the user's Supabase profile ID from Django User model.
    """
    supabase_id = getattr(user, "supabase_id", None)
    return supabase_id if supabase_id else None


# ------------------------
# Slang words (Pinecone + Supabase)
# ------------------------
@login_required
@user_passes_test(lambda u: u.role in ["admin", "moderator"])
def manage_slang_words(request):
    logger.info("manage_slang_words called, method=%s", request.method)
    if request.method != "POST":
        return redirect("dashboard_home")

    form = SlangWordForm(request.POST)
    if not form.is_valid():
        for f, errs in form.errors.items():
            for e in errs:
                messages.error(request, f"{f}: {e}")
        return redirect("dashboard_home")

    word = form.cleaned_data["word"].lower().strip()
    action = form.cleaned_data["action"]

    try:
        # check duplication in supabase
        resp = supabase.from_("slang_words").select("id").eq("word", word).execute()
        exists = resp.data and len(resp.data) > 0

        if action == "add":
            if exists:
                messages.warning(request, f'"{word}" is already in restricted words.')
                return redirect("dashboard_home")

            # Pinecone embed + upsert
            embedding = get_embedding(word)
            pinecone_index.upsert(vectors=[{
                "id": f"slang_{word}",
                "values": embedding,
                "metadata": {"type": "slang", "word": word, "added_by": request.user.username}
            }])

            # Insert into supabase
            profile_id = get_user_supabase_id(request.user)
            r = supabase.from_("slang_words").insert({
                "word": word,
                "added_by": profile_id,
                "is_active": True
            }).execute()

            messages.success(request, f'Successfully added "{word}" to restricted words.')

        elif action == "delete":
            if not exists:
                messages.error(request, f'"{word}" not found.')
                return redirect("dashboard_home")

            # Pinecone delete
            pinecone_index.delete(ids=[f"slang_{word}"])

            # Supabase delete
            supabase.from_("slang_words").delete().eq("word", word).execute()

            messages.success(request, f'Successfully removed "{word}" from restricted words.')

    except Exception as e:
        logger.exception("Error manage_slang_words")
        messages.error(request, f"Error processing restricted words: {e}")

    return redirect("dashboard_home")


# ------------------------
# Post a comment -> Supabase
# ------------------------
@login_required
def post_comment_view(request):
    if request.method != "POST":
        return render(request, "moderation/post_comment.html", {"form": ContentForm()})

    form = ContentForm(request.POST)
    if not form.is_valid():
        for f, errs in form.errors.items():
            for e in errs:
                messages.error(request, f"{f}: {e}")
        return redirect("dashboard_home")

    try:
        text = form.cleaned_data["text"]
        profile_id = get_user_supabase_id(request.user)

        # Run moderation pipeline
        result = predict_all(text)
        spam = result.get("spam", 0.0)
        phishing = result.get("phishing", 0.0)
        toxicity = result.get("toxic", 0.0)
        drug = result.get("drug", 0.0)
        safe_score = result.get("safe_score", 0.0)
        final_label = result.get("final_label", "safe")
        reasons = result.get("reasons", []) or []

        # Decide status
        if final_label == "safe":
            status = "safe"; action = "allow"
        elif final_label == "review":
            status = "flagged"; action = "review"
        else:
            status = "banned"; action = "ban"

        # Insert contents
        ins = supabase.from_("contents").insert({
            "user_id": profile_id,
            "text": text,
            "status": status
        }).execute()

        inserted = ins.data[0] if isinstance(ins.data, list) else ins.data
        content_id = inserted.get("id")

        # Insert moderation_results
        mod_res = supabase.from_("moderation_results").insert({
            "content_id": content_id,
            "label": final_label,
            "confidence_score": safe_score,
            "action": action,
            "spam_score": spam,
            "ham_score": max(0, 1 - spam),
            "phishing_score": phishing,
            "legitimate_score": max(0, 1 - phishing),
            "drug_score": drug,
            "toxic_score": toxicity,
            "non_toxic_score": max(0, 1 - toxicity),
            "safe_score": safe_score,
            "reasons": reasons,
        }).execute()

        moderation_id = mod_res.data[0]["id"]

        # Insert audit_logs (this was missing!)
        supabase.from_("audit_logs").insert({
            "user_id": profile_id,
            "action": action,
            "content_id": content_id,
            "moderation_result_id": moderation_id,   # correct column
            "notes": "; ".join(reasons) if reasons else None,   # correct column
        }).execute()


        # UI messages
        if status == "safe":
            messages.success(request, "Comment posted successfully! 🎉")
        elif status == "flagged":
            messages.warning(request, f"Your comment is flagged for review.")
        else:
            messages.error(request, f"Your comment was blocked. Reason: {', '.join(reasons)}")

    except Exception as e:
        logger.exception("Error in post_comment_view")
        messages.error(request, f"Error posting comment: {e}")

    return redirect("dashboard_home")


# ------------------------
# My comments (fetch from supabase)
# ------------------------
@login_required
def my_comments_view(request):
    profile_id = get_user_supabase_id(request.user)

    try:
        # Fetch user's comments
        resp = supabase.from_("contents") \
                       .select("*") \
                       .eq("user_id", profile_id) \
                       .order("created_at", desc=True) \
                       .execute()

        rows = resp.data or []
        comments = []

        for r in rows:
            # Fetch author profile
            profile_row = None
            if r.get("user_id"):
                p = supabase.from_("profiles") \
                            .select("id,username,email") \
                            .eq("id", r.get("user_id")) \
                            .single() \
                            .execute()
                profile_row = p.data  # safe: None if not found

            # Fetch latest moderation entry
            mr = supabase.from_("moderation_results") \
                         .select("*") \
                         .eq("content_id", r.get("id")) \
                         .order("created_at", desc=True) \
                         .limit(1) \
                         .execute()

            latest_mod = mr.data[0] if mr.data else None

            comments.append(_row_to_content_obj(r, profile_row, latest_mod))

    except Exception as e:
        logger.exception("my_comments_view failed")
        messages.error(request, "Failed to load your comments.")
        comments = []

    return render(request, "moderation/my_comments.html", {"comments": comments})


@login_required
def flagged_comments_view(request):
    if not (request.user.role in ["admin", "moderator"] or request.user.is_staff):
        return redirect("dashboard_home")

    try:
        resp = supabase.from_("contents") \
                       .select("*") \
                       .eq("status", "flagged") \
                       .order("created_at", desc=True) \
                       .execute()

        rows = resp.data or []
        flagged = []

        for r in rows:
            # Fetch content author profile
            profile_row = None
            if r.get("user_id"):
                p = supabase.from_("profiles") \
                            .select("id,username,email") \
                            .eq("id", r.get("user_id")) \
                            .single() \
                            .execute()

                profile_row = p.data

            # Latest moderation
            latest_mod_resp = supabase.from_("moderation_results") \
                                      .select("*") \
                                      .eq("content_id", r.get("id")) \
                                      .order("created_at", desc=True) \
                                      .limit(1) \
                                      .execute()

            latest_mod = latest_mod_resp.data[0] if latest_mod_resp.data else None

            flagged.append(_row_to_content_obj(r, profile_row, latest_mod))

        # Build mapping for template
        moderation_results = {}
        for c in flagged:
            if c.moderation_results:
                mr = c.moderation_results[0]
                moderation_results[c.id] = {
                    "spam_score": mr.spam_score,
                    "phishing_score": mr.phishing_score,
                    "toxic_score": mr.toxic_score,
                    "drug_score": mr.drug_score,
                    "safe_score": mr.safe_score,
                    "confidence": mr.confidence_score,
                    "reasons": mr.reasons,
                }

    except Exception as e:
        logger.exception("flagged_comments_view failed")
        messages.error(request, "Failed to load flagged comments.")
        flagged = []
        moderation_results = {}

    return render(request, "moderation/flagged_comments.html", {
        "comments": flagged,
        "moderation_results": moderation_results,
    })


@login_required
def give_feedback_view(request, result_id):

    try:
        mr_resp = supabase.from_("moderation_results") \
                          .select("*") \
                          .eq("id", result_id) \
                          .single() \
                          .execute()

        mr_row = mr_resp.data
        if not mr_row:
            messages.error(request, "Moderation result not found.")
            return redirect("flagged_comments")

    except Exception as e:
        logger.exception("Failed loading moderation result")
        messages.error(request, "Failed to load moderation result.")
        return redirect("flagged_comments")

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Invalid feedback form.")
            return redirect("flagged_comments")

        payload = {
            "moderator_id": get_user_supabase_id(request.user),
            "moderation_result_id": result_id,
            "decision": form.cleaned_data["decision"],
            "moderator_notes": form.cleaned_data.get("moderator_notes", "")
        }

        try:
            supabase.from_("feedbacks").insert(payload).execute()

            # audit log
            supabase.from_("audit_logs").insert({
                "user_id": get_user_supabase_id(request.user),
                "action": "feedback_given",
                "content_id": mr_row.get("content_id"),
                "moderation_result_id": result_id,
                "notes": payload["moderator_notes"]
            }).execute()

            messages.success(request, "Feedback submitted!")

        except Exception as e:
            logger.exception("give_feedback_view")
            messages.error(request, f"Error submitting feedback: {e}")

        return redirect("flagged_comments")

    return render(request, "moderation/feedback.html", {
        "form": FeedbackForm(),
        "result": SimpleNamespace(**mr_row),
    })

@login_required
def review_content_view(request, content_id):
    if not (request.user.role in ["admin", "moderator"] or request.user.is_staff):
        return redirect("dashboard_home")

    # Fetch content
    resp = supabase.from_("contents") \
                   .select("*") \
                   .eq("id", content_id) \
                   .single() \
                   .execute()

    content_row = resp.data
    if not content_row:
        messages.error(request, "Content not found.")
        return redirect("moderation:flagged_comments")

    # ================================
    #        POST ACTIONS
    # ================================
    if request.method == "POST":
        action = request.POST.get("action")
        profile_id = request.user.supabase_id

        if action == "approve":
            # Update content
            supabase.from_("contents").update({"status": "safe"}) \
                .eq("id", content_id).execute()

            # Update moderation_results
            mod_res = supabase.from_("moderation_results").update({
                "action": "allow",
                "label": "safe",
                "safe_score": 1.0
            }).eq("content_id", content_id).execute()

            moderation_result_id = mod_res.data[0]["id"] if mod_res.data else None

            # ⭐ FIXED: Convert UUIDs to STRING before inserting
            supabase.from_("audit_logs").insert({
                "user_id": str(profile_id),
                "action": "approved",
                "content_id": str(content_id),
                "moderation_result_id": str(moderation_result_id) if moderation_result_id else None,
                "notes": "Admin approved the content."
            }).execute()

            messages.success(request, "Content approved.")

        elif action == "reject":
            # Update content
            supabase.from_("contents").update({"status": "banned"}) \
                .eq("id", content_id).execute()

            # Update moderation_results
            mod_res = supabase.from_("moderation_results").update({
                "action": "ban",
                "label": "banned",
                "safe_score": 0.0
            }).eq("content_id", content_id).execute()

            moderation_result_id = mod_res.data[0]["id"] if mod_res.data else None

            # ⭐ FIXED: Convert UUIDs to STRING before inserting
            supabase.from_("audit_logs").insert({
                "user_id": str(profile_id),
                "action": "banned",
                "content_id": str(content_id),
                "moderation_result_id": str(moderation_result_id) if moderation_result_id else None,
                "notes": "Admin rejected the content."
            }).execute()

            messages.warning(request, "Content rejected.")

        return redirect("moderation:flagged_comments")

    # ================================
    #        GET — Load for Page
    # ================================
    mr_resp = supabase.from_("moderation_results") \
                      .select("*") \
                      .eq("content_id", content_id) \
                      .order("created_at", desc=True) \
                      .limit(1) \
                      .execute()

    latest_mod = mr_resp.data[0] if mr_resp.data else None

    return render(request, "moderation/review_content.html", {
        "content": SimpleNamespace(**content_row),
        "moderation_result": SimpleNamespace(**(latest_mod or {})),
    })

@require_POST
@login_required
@user_passes_test(lambda u: u.role in ["admin", "moderator"])
def delete_slang_word(request, word_id):
    try:
        sel = supabase.from_("slang_words") \
                      .select("word") \
                      .eq("id", str(word_id)) \
                      .execute()

        if not sel.data:
            messages.error(request, "Word not found.")
            return redirect("dashboard_home")

        word = sel.data[0]["word"]

        # Delete from Pinecone
        pinecone_index.delete(ids=[f"slang_{word}"])

        # Delete from Supabase
        supabase.from_("slang_words").delete().eq("id", str(word_id)).execute()

        messages.success(request, f"Removed '{word}'")
    except Exception as e:
        logger.exception("delete_slang_word failed")
        messages.error(request, f"Error: {e}")

    return redirect("dashboard_home")

# ------------------------
# Quick review (AJAX)
# # ------------------------
# @login_required
# def quick_review_view(request, content_id):
#     if request.method != "POST":
#         return JsonResponse({"error": "Method not allowed"}, status=405)

#     if request.user.role not in ["admin", "moderator"] and not request.user.is_staff:
#         return JsonResponse({"error": "Permission denied"}, status=403)

#     action = request.POST.get("action")
#     try:
#         if action == "approve":
#             supabase.from_("contents").update({"status": "safe"}).eq("id", content_id).execute()
#             supabase.from_("moderation_results") \
#                 .update({"action": "allow", "label": "safe", "safe_score": 1.0}) \
#                 .eq("content_id", content_id).execute()
#             return JsonResponse({"status": "approved"})

#         elif action == "reject":
#             supabase.from_("contents").update({"status": "banned"}).eq("id", content_id).execute()
#             supabase.from_("moderation_results") \
#                 .update({"action": "ban", "label": "banned", "safe_score": 0.0}) \
#                 .eq("content_id", content_id).execute()
#             return JsonResponse({"status": "rejected"})

#         else:
#             return JsonResponse({"error": "Invalid action"}, status=400)

#     except Exception as e:
#         logger.exception("quick_review_view")
#         return JsonResponse({"error": str(e)}, status=500)
