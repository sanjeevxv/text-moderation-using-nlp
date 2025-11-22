import os
import torch
from transformers import DistilBertTokenizerFast, DistilBertForSequenceClassification
from ai_models.hf_settings import HF_TOKEN, repo

LOCAL_DIR = os.path.join(os.path.dirname(__file__), "saved_phishing_transformer_best")
HF_REPO = repo("phishing-transformer-best")

_tokenizer = None
_model = None


def load_phishing_model():
    global _tokenizer, _model

    if _tokenizer and _model:
        return _tokenizer, _model

    try:
        print("Loading Phishing Model from HuggingFace…")
        _tokenizer = DistilBertTokenizerFast.from_pretrained(HF_REPO, use_auth_token=HF_TOKEN)
        _model = DistilBertForSequenceClassification.from_pretrained(HF_REPO, use_auth_token=HF_TOKEN)
    except Exception:
        print("⚠ HF download failed — using LOCAL model.")
        _tokenizer = DistilBertTokenizerFast.from_pretrained(LOCAL_DIR, local_files_only=True)
        _model = DistilBertForSequenceClassification.from_pretrained(LOCAL_DIR, local_files_only=True)

    _model.eval()
    return _tokenizer, _model


def predict_phishing_transformer(text):
    if not text or not isinstance(text, str):
        return {"phishing": 0.0, "legitimate": 1.0}

    tokenizer, model = load_phishing_model()

    enc = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=256)
    with torch.no_grad():
        logits = model(**enc).logits

    probs = torch.softmax(logits, dim=1)[0]

    return {
        "phishing": round(probs[1].item(), 4),
        "legitimate": round(probs[0].item(), 4)
    }
