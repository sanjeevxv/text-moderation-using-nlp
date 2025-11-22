# ai_models/drug_embeddings.py
import os
import joblib
import numpy as np
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from .drug_keywords import DRUG_KEYWORDS

BASE = os.path.dirname(__file__)

# =====================
# EMBEDDING MODEL
# =====================
EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")

# =====================
# PINECONE INITIALIZATION
# =====================
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX", "safenet-blocklist")     # 🔥 FIXED

pc = None
index = None

if not PINECONE_API_KEY:
    print("❌ PINECONE_API_KEY missing! Pinecone disabled.")
else:
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)

        # Create index if missing
        existing = [i["name"] for i in pc.list_indexes()]
        if INDEX_NAME not in existing:
            print(f"⚠️ Creating Pinecone index: {INDEX_NAME}")
            pc.create_index(
                name=INDEX_NAME,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )

        index = pc.Index(INDEX_NAME)
        print(f"✅ Connected to Pinecone index: {INDEX_NAME}")

    except Exception as e:
        print("❌ ERROR initializing Pinecone:", e)
        index = None


# =====================
# LOGISTIC MODEL
# =====================
CLASSIFIER = joblib.load(os.path.join(BASE, "embedding_logistic.pkl"))


# =====================
# EMBEDDING UTILITIES
# =====================
def get_embedding(text):
    """Generate a 384-dim embedding vector."""
    return EMBEDDER.encode(text).tolist()


# =====================
# RETRIEVAL FEATURES FROM PINECONE
# =====================
def get_retrieval_features(text, k=5):
    """Return similarity features from Pinecone filtered only for drug tokens."""
    if not index:
        return {"avg_score": 0, "pct_drug_neighbors": 0, "min_distance": 1}

    emb = get_embedding(text)

    # 🔥 IMPORTANT FIX — FILTER BY category="drug"
    res = index.query(
        vector=emb,
        top_k=k,
        include_metadata=True,
        filter={"category": "drug"}   # ONLY check drug vectors
    )

    matches = res.get("matches", [])

    if not matches:
        return {"avg_score": 0, "pct_drug_neighbors": 0, "min_distance": 1}

    scores = [m["score"] for m in matches]
    labels = [m["metadata"].get("label", 0) for m in matches]

    return {
        "avg_score": float(np.mean(scores)),
        "pct_drug_neighbors": float(np.mean(labels)),
        "min_distance": float(1 - max(scores))
    }


# =====================
# CONTEXT BOOST
# =====================
def context_boost(text):
    """Detect sale or transactional language."""
    text = text.lower()
    sale_words = [
        "buy", "sell", "supply",
        "dealer", "dm", "message me",
        "hit me up", "asap", "plug"
    ]

    for w in sale_words:
        if w in text:
            return 1.0

    return 0.0


# =====================
# KEYWORD BOOST
# =====================
def keyword_boost(text):
    text_lower = text.lower()
    for k, score in DRUG_KEYWORDS.items():
        if k in text_lower:
            return score
    return 0.0


# =====================
# FINAL DRUG PROBABILITY
# =====================
def predict_drug_probability(text):
    """
    Combines:
    - Logistic Regression classifier
    - Pinecone similarity
    - Drug keyword weight
    - Context words boost
    """
    emb = np.array(get_embedding(text)).reshape(1, -1)

    logistic_prob = CLASSIFIER.predict_proba(emb)[0][1]

    retrieval = get_retrieval_features(text)
    pinecone_score = retrieval["pct_drug_neighbors"]
    key_score = keyword_boost(text)
    context = context_boost(text)

    final_prob = (
        0.40 * logistic_prob +
        0.35 * pinecone_score +
        0.20 * key_score +
        0.05 * context
    )

    return float(min(max(final_prob, 0), 1))


# =====================
# STORE DRUG TERM IN PINECONE
# =====================
def add_drug_vector(word, user="system"):
    """Add a drug-related keyword to the blocklist index."""
    if not index:
        return {"error": "Pinecone not available"}

    vector = get_embedding(word)

    return index.upsert(
        vectors=[{
            "id": f"drug_{word.lower()}",
            "values": vector,
            "metadata": {
                "text": word.lower(),
                "category": "drug",   # 🔥 FIXED
                "label": 1,
                "added_by": user
            }
        }]
    )


# =====================
# DELETE DRUG TERM
# =====================
def delete_drug_vector(word):
    if not index:
        return {"error": "Pinecone not available"}

    return index.delete(ids=[f"drug_{word.lower()}"])
