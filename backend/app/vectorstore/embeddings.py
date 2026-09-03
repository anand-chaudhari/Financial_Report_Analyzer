from typing import List
import threading
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

_embedding_model = None
_embedder_lock = threading.Lock()


class SafeEmbedder:
    """
    High-performance wrapper around SentenceTransformer with torch inference_mode
    that always returns List[List[float]].
    """

    def __init__(self, model):
        self._model = model

    def encode(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Encode texts and always return a plain list-of-lists of Python floats."""
        if not texts:
            return []

        settings = get_settings()
        batch_size = kwargs.pop("batch_size", getattr(settings, "EMBEDDING_BATCH_SIZE", 256))
        kwargs.setdefault("batch_size", batch_size)
        kwargs.setdefault("convert_to_numpy", True)
        kwargs.setdefault("show_progress_bar", False)
        kwargs.setdefault("normalize_embeddings", True)

        try:
            import torch
            with torch.inference_mode():
                raw = self._model.encode(texts, **kwargs)
        except Exception:
            raw = self._model.encode(texts, **kwargs)

        # Convert whatever we got into list[list[float]]
        if hasattr(raw, "tolist"):
            result = raw.tolist()
        elif isinstance(raw, list):
            result = []
            for row in raw:
                if hasattr(row, "tolist"):
                    result.append(row.tolist())
                elif isinstance(row, list):
                    result.append(row)
                else:
                    result.append(list(row))
        else:
            result = list(raw)

        return result


def get_embedding_function() -> SafeEmbedder:
    """
    Returns a SafeEmbedder wrapping SentenceTransformer.
    Reuses one global singleton instance for all embedding operations.
    """
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    with _embedder_lock:
        if _embedding_model is not None:
            return _embedding_model

        settings = get_settings()
        model_name = settings.EMBEDDING_MODEL_NAME

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading SentenceTransformers embedding model: {model_name}...")
            base_model = SentenceTransformer(model_name)
            # Warm up with a tiny token
            _ = base_model.encode(["FinSight AI"], convert_to_numpy=True)
            _embedding_model = SafeEmbedder(base_model)
            logger.info("SentenceTransformers model initialized, warmed up, and wrapped in SafeEmbedder.")
            return _embedding_model
        except Exception as e:
            logger.error(f"Failed to load embedding model '{model_name}': {str(e)}")

            class FallbackEmbedder:
                def encode(self, texts: List[str], **kwargs) -> List[List[float]]:
                    return [[0.0] * 384 for _ in texts]

            _embedding_model = FallbackEmbedder()
            return _embedding_model
