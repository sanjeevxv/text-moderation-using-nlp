# import os
# import joblib
# import numpy as np
# from pinecone import Pinecone
# from sentence_transformers import SentenceTransformer

# # ----------------------------------------
# # 1. Load Embedding Model (once)
# # ----------------------------------------
# try:
#     embedder = SentenceTransformer("all-MiniLM-L6-v2")
# except Exception as e:
#     print("❌ Failed to load embedding model:", e)
#     embedder = None


# # ----------------------------------------
# # 2. Pinecone Setup (secure)
# # ----------------------------------------
# PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")  # <---- use environment variable
# INDEX_NAME = "drug-slang-index-384"
# HOST_URL = "https://drug-slang-index-384-x5hdije.svc.aped-4627-b74a.pinecone.io"

# pc = None
# index = None

# try:
#     pc = Pinecone(api_key=PINECONE_API_KEY)
#     index = pc.Index(INDEX_NAME, host=HOST_URL)
# except Exception as e:
#     print("❌ Pinecone initialization error:", e)


# # ----------------------------------------
# # 3. Load Logistic Regression Classifier
# # ----------------------------------------
# MODEL_PATH = os.path.join(os.path.dirname(__file__), "embedding_logistic.pkl")

# try:
#     classifier = joblib.load(MODEL_PATH)
# except Exception as e:
#     print("❌ Failed to load classifier:", e)
#     classifier = None


# # ----------------------------------------
# # 4. Functions
# # ----------------------------------------

# def get_embedding(text: str):
#     """Generate 384-D embedding."""
#     try:
#         return embedder.encode(text).tolist()
#     except Exception as e:
#         print("❌ Embedding error:", e)
#         return [0.0] * 384  # fallback


# def get_retrieval_features(text: str, k=5):
#     """Query Pinecone safely and return retrieval metrics."""
#     if index is None:
#         return {"avg_score": 0.0, "pct_drug_neighbors": 0.0, "min_distance": 1.0}

#     emb = get_embedding(text)
#     try:
#         res = index.query(vector=emb, top_k=k, include_metadata=True)
#         matches = res.get("matches", [])
#     except Exception as e:
#         print("❌ Pinecone query error:", e)
#         return {"avg_score": 0.0, "pct_drug_neighbors": 0.0, "min_distance": 1.0}

#     if not matches:
#         return {"avg_score": 0.0, "pct_drug_neighbors": 0.0, "min_distance": 1.0}

#     scores = [m["score"] for m in matches]
#     labels = [int(m["metadata"].get("label", 0)) for m in matches]

#     return {
#         "avg_score": float(np.mean(scores)),
#         "pct_drug_neighbors": float(np.mean(labels)),
#         "min_distance": float(1 - max(scores))
#     }


# def predict_drug_probability(text: str):
#     """Final probability using logistic regression classifier."""
#     if classifier is None:
#         return 0.0

#     emb = np.array(get_embedding(text)).reshape(1, -1)
#     try:
#         return float(classifier.predict_proba(emb)[0][1])
#     except Exception as e:
#         print("❌ Classifier error:", e)
#         return 0.0
