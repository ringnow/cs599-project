"""Embedding model wrapper — lazy-loaded singleton.

Uses sentence-transformers/all-MiniLM-L6-v2 by default (384-dim, CPU-friendly).
The model is loaded on first use, not at import time, so the server starts
fast even when RAG is never used.
"""
import os
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

# Module-level singleton; None until first call.
_model = None


def get_model():
    """Return the singleton SentenceTransformer, loading it on first call."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            device = os.getenv("EMBEDDING_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
            logger.info("Loading embedding model: %s (device=%s)", _MODEL_NAME, device)
            _model = SentenceTransformer(_MODEL_NAME, device=device)
            logger.info("Embedding model loaded (dim=%d, device=%s)", _model.get_sentence_embedding_dimension(), device)
        except ImportError:
            logger.warning(
                "sentence-transformers not installed; RAG features disabled. "
                "Run: pip install sentence-transformers"
            )
            raise
        except Exception as e:
            logger.warning("Failed to load embedding model %s: %s", _MODEL_NAME, e)
            raise
    return _model


def embed(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts. Returns normalized vectors."""
    if not texts:
        return []
    model = get_model()
    return model.encode(texts, normalize_embeddings=True).tolist()


def embed_one(text: str) -> List[float]:
    """Convenience: embed a single string."""
    return embed([text])[0]


def is_available() -> bool:
    """Check if the embedding model can be loaded (without actually loading)."""
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False
