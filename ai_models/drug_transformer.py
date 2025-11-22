import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from ai_models.hf_settings import HF_TOKEN, repo

LOCAL_DIR = os.path.join(os.path.dirname(__file__), "saved_drug_transformer_best")
HF_REPO = repo("drug-transformer-best")

_tokenizer = None
_model = None


def load_drug_model():
    global _tokenizer, _model

    if _tokenizer and _model:
        return _tokenizer, _model

    try:
        print("Loading Drug Model from HuggingFace…")
        _tokenizer = AutoTokenizer.from_pretrained(HF_REPO, use_auth_token=HF_TOKEN)
        _model = AutoModelForSequenceClassification.from_pretrained(HF_REPO, use_auth_token=HF_TOKEN)
    except Exception:
        print("⚠ HF download failed — using LOCAL model.")

        _tokenizer = AutoTokenizer.from_pretrained(LOCAL_DIR, local_files_only=True)
        _model = AutoModelForSequenceClassification.from_pretrained(LOCAL_DIR, local_files_only=True)

    _model.eval()
    return _tokenizer, _model


def predict_drug_transformer(text):
    if not text or not isinstance(text, str):
        return {"drug": 0.0, "not_drug": 1.0, "safe": True}

    tokenizer, model = load_drug_model()
    inputs = tokenizer(text, truncation=True, padding=True, max_length=256, return_tensors="pt")

    with torch.no_grad():
        logits = model(**inputs).logits

    probs = torch.softmax(logits, dim=1)[0]
    return {
        "drug": round(probs[1].item(), 4),
        "not_drug": round(probs[0].item(), 4),
        "safe": probs[0].item() > 0.5
    }
