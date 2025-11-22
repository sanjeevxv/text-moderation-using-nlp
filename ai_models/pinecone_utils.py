# ai_models/pinecone_utils.py

from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# 🔥 INIT PINECONE
# ============================================
def get_pinecone_index():
    load_dotenv()

    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("Missing PINECONE_API_KEY")

    # ALWAYS USE THIS INDEX
    index_name = os.getenv("PINECONE_INDEX", "safenet-blocklist")

    pc = Pinecone(api_key=api_key)

    # Check existing indexes
    existing = [idx.name for idx in pc.list_indexes()]
    print("Existing:", existing)

    if index_name not in existing:
        print(f"Creating index {index_name}")
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )

    index = pc.Index(index_name)
    print(f"✅ Using Pinecone index: {index_name}")
    return index


# Single global instance
index = get_pinecone_index()

# ============================================
# 🔥 LOAD EMBEDDING MODEL
# ============================================
model = SentenceTransformer("all-MiniLM-L6-v2")


# ============================================
# 🔥 EMBEDDING FUNCTION
# ============================================
def get_embedding(text: str):
    vector = model.encode([text])[0].tolist()
    return vector


# ============================================
# 🔥 ADD TEXT → UNIFIED BLOCKLIST
# ============================================
def store_text(text: str, added_by: str, category="generic"):
    """
    category can be:
    - phishing
    - slang
    - drug
    - generic
    """
    vector = get_embedding(text)
    vector_id = f"{category}_{text.lower()}"

    meta = {
        "text": text.lower(),
        "category": category,
        "added_by": added_by
    }

    response = index.upsert([
        {"id": vector_id, "values": vector, "metadata": meta}
    ])

    return response


# ============================================
# 🔥 CHECK SIMILARITY
# ============================================
def check_text(text: str, threshold=0.80, category=None):
    """
    category filter optional
    category="phishing" or "slang" or "drug"
    """

    vector = get_embedding(text)

    query_params = {
        "vector": vector,
        "top_k": 1,
        "include_metadata": True
    }

    if category:
        query_params["filter"] = {"category": category}

    result = index.query(**query_params)

    if not result.get("matches"):
        return False, 0, None

    match = result["matches"][0]
    score = match["score"]
    matched_text = match["metadata"].get("text")

    if score >= threshold:
        return True, score, matched_text

    return False, score, matched_text


# ============================================
# 🔥 DELETE ENTRY
# ============================================
def delete_text(text: str, category="generic"):
    vector_id = f"{category}_{text.lower()}"
    index.delete(ids=[vector_id])
    return True
