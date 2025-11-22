from ai_models.transformer_spam import predict_spam
from ai_models.toxicity_transformer import predict_toxicity
from ai_models.drug_transformer import predict_drug_transformer
from ai_models.phishing_transformer import predict_phishing_transformer
from ai_models.pinecone_utils import check_text


def predict_all(text):
    """
    Unified moderation pipeline for SafeNet.
    Applies strict blocklist, short-text logic, and multi-model scoring.
    Scores:
        - Ban        : safe_score < 0.35
        - Review     : 0.35 <= safe_score < 0.75
        - Safe       : safe_score >= 0.75
    """

    text_clean = text.strip()

    # ----------------------------------------------------------------------
    # 0) STRICT BLOCKLIST CHECK (Pinecone)
    # ----------------------------------------------------------------------
    try:
        is_match, similarity, matched_text = check_text(text_clean, threshold=0.80)
    except Exception as e:
        print("Pinecone error:", e)
        is_match, similarity, matched_text = False, 0.0, None

    # Strong match threshold for banning
    if is_match and matched_text and similarity >= 0.95:
        print("\n🚨 STRICT BLOCKLIST MATCH — AUTO BAN")
        print(f"Matched: {matched_text} (sim={similarity:.2f})\n")

        return {
            "spam": 0.0,
            "toxic": 0.0,
            "phishing": 1.0,
            "drug": 0.0,
            "safe_score": 0.0,
            "final_label": "unsafe",
            "reasons": [f"Blocklisted term detected: '{matched_text}'"],
            "safe": False,
        }

    # ----------------------------------------------------------------------
    # 1) SHORT TEXT RULE – ONLY TOXICITY & DRUG (under 15 chars)
    # ----------------------------------------------------------------------
    if len(text_clean) < 15:
        print("\n⚠️ SHORT TEXT — LIMITED ANALYSIS (Toxicity + Drug Only)\n")

        # Re-check Pinecone with a slightly lower threshold on short text
        try:
            short_match, sim2, short_matched = check_text(text_clean, threshold=0.75)
        except:
            short_match = False

        if short_match:
            print("\n🚨 SHORT TEXT BLOCKLIST MATCH — AUTO BAN\n")
            return {
                "spam": 0.0,
                "toxic": 0.0,
                "phishing": 0.0,
                "drug": 1.0,
                "safe_score": 0.0,
                "final_label": "unsafe",
                "reasons": [f"Blocklisted term detected: '{short_matched}'"],
                "safe": False,
            }

        # Toxicity
        tox_res = predict_toxicity(text_clean)
        if isinstance(tox_res, dict):
            toxic = float(tox_res.get("toxic", 0.0))
        else:
            t_label, t_conf = tox_res
            toxic = float(t_conf) if t_label == 1 else (1 - float(t_conf))

        # Drug
        try:
            drug = float(predict_drug_transformer(text_clean).get("drug", 0.0))
        except:
            drug = 0.0

        # Scoring for short messages
        unsafe_score = (toxic * 0.40) + (drug * 0.60)
        safe_score = 1 - unsafe_score

        # --- Apply Universal Rules (Same as full text) ---
        if safe_score < 0.35:
            final_label = "unsafe"
        elif safe_score < 0.75:
            final_label = "review"
        else:
            final_label = "safe"

        reasons = ["Short text: spam/phishing skipped"]
        if drug > 0.7:
            reasons.append(f"High drug content ({drug:.2f})")
        if toxic > 0.7:
            reasons.append(f"High toxicity ({toxic:.2f})")

        print("\n=== DEBUG (SHORT TEXT) ===")
        print("Toxic:", toxic)
        print("Drug:", drug)
        print("Safe Score:", safe_score)
        print("==========================\n")

        return {
            "spam": 0.0,
            "toxic": toxic,
            "phishing": 0.0,
            "drug": drug,
            "safe_score": safe_score,
            "final_label": final_label,
            "reasons": reasons,
            "safe": final_label == "safe",
        }

    # ----------------------------------------------------------------------
    # 2) FULL PIPELINE FOR NORMAL TEXT
    # ----------------------------------------------------------------------

    # Spam
    s_label, s_conf = predict_spam(text_clean)
    try:
        spam = max(0.0, min(1.0, float(s_conf)))
    except:
        spam = 0.0

    # Toxicity
    tox_res = predict_toxicity(text_clean)
    if isinstance(tox_res, dict):
        toxic = float(tox_res.get("toxic", 0.0))
    else:
        t_label, t_conf = tox_res
        toxic = float(t_conf) if t_label == 1 else (1 - float(t_conf))

    # Phishing
    try:
        phishing = float(predict_phishing_transformer(text_clean).get("phishing", 0.0))
    except:
        phishing = 0.0

    # Drug
    try:
        drug = float(predict_drug_transformer(text_clean).get("drug", 0.0))
    except:
        drug = 0.0

    # Weighted unsafe calculation
    unsafe_score = (
        (spam * 0.20)
        + (phishing * 0.25)
        + (toxic * 0.25)
        + (drug * 0.30)
    )
    safe_score = 1 - unsafe_score

    # Final label
    if safe_score < 0.35:
        final_label = "unsafe"
    elif safe_score < 0.75:
        final_label = "review"
    else:
        final_label = "safe"

    # Build reasons
    reasons = []
    if spam > 0.7:
        reasons.append(f"High spam ({spam:.2f})")
    if toxic > 0.7:
        reasons.append(f"Toxic content ({toxic:.2f})")
    if phishing > 0.7:
        reasons.append(f"Phishing risk ({phishing:.2f})")
    if drug > 0.7:
        reasons.append(f"Drug-related content ({drug:.2f})")

    print("\n=== DEBUG MODEL OUTPUTS ===")
    print("Spam:", spam)
    print("Phishing:", phishing)
    print("Toxic:", toxic)
    print("Drug:", drug)
    print("Safe Score:", safe_score)
    print("=================================\n")

    return {
        "spam": spam,
        "toxic": toxic,
        "phishing": phishing,
        "drug": drug,
        "safe_score": safe_score,
        "final_label": final_label,
        "reasons": reasons,
        "safe": final_label == "safe",
    }
