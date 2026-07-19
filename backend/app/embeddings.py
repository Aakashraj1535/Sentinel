"""
Shared embedding model loader (sentence-transformers, all-MiniLM-L6-v2).
Loaded once and reused — loading it fresh every call would be slow.
"""

from sentence_transformers import SentenceTransformer

_model = None


def get_embedder():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_text(text: str):
    model = get_embedder()
    return model.encode(text).tolist()
