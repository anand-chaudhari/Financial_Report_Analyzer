from typing import List, Optional
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

_embedding_model = None


def get_embedding_function():
    """
    Returns SentenceTransformers embedding model instance.
    Lazy loaded on first request to optimize server startup time.
    """
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    settings = get_settings()
    model_name = settings.EMBEDDING_MODEL_NAME

    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading SentenceTransformers embedding model: {model_name}...")
        _embedding_model = SentenceTransformer(model_name)
        logger.info("SentenceTransformers model loaded successfully.")
        return _embedding_model
    except Exception as e:
        logger.error(f"Failed to load embedding model '{model_name}': {str(e)}")
        # Fallback dummy embedder for lightweight local testing
        class FallbackEmbedder:
            def encode(self, texts: List[str], **kwargs):
                return [[0.0] * 384 for _ in texts]
        return FallbackEmbedder()
