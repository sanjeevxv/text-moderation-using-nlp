import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from ai_models.hf_settings import HF_TOKEN, repo

LOCAL_DIR = os.path.join(os.path.dirname(__file__), "saved_spam_transformer_best")
HF_REPO = repo("spam-transformer-best")

_tokenizer = None
_model = None


def load_spam_model():
    global _tokenizer, _model

    if _tokenizer and _model:
        return _tokenizer, _model

    try:
        print("Loading Spam Model from HuggingFace…")
        _tokenizer = AutoTokenizer.from_pretrained(HF_REPO, use_auth_token=HF_TOKEN)
        _model = AutoModelForSequenceClassification.from_pretrained(HF_REPO, use_auth_token=HF_TOKEN)
    except Exception:
        print("⚠ HF download failed — using LOCAL model.")
        _tokenizer = AutoTokenizer.from_pretrained(LOCAL_DIR, local_files_only=True)
        _model = AutoModelForSequenceClassification.from_pretrained(LOCAL_DIR, local_files_only=True)

    _model.eval()
    return _tokenizer, _model


def predict_spam(text):
    tokenizer, model = load_spam_model()

    enc = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=256)
    with torch.no_grad():
        logits = model(**enc).logits

    probs = torch.softmax(logits, dim=1)[0]
    label = torch.argmax(probs).item()

    return label, float(probs[label].item())
