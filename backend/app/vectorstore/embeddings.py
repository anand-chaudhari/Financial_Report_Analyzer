from typing import List
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

_embedding_model = None


class SafeEmbedder:
    """
    Wrapper around SentenceTransformer that always returns List[List[float]]
    regardless of whether encode() returns ndarray, Tensor, or list-of-arrays.
    This permanently eliminates the .tolist() AttributeError on lists.
    """

    def __init__(self, model):
        self._model = model

    def encode(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Encode texts and always return a plain list-of-lists of Python floats."""
        # Always request numpy output (avoids torch Tensor surprises)
        kwargs.setdefault("convert_to_numpy", True)
        kwargs.setdefault("show_progress_bar", False)
        raw = self._model.encode(texts, **kwargs)

        # Convert whatever we got into list[list[float]]
        if hasattr(raw, "tolist"):
            # numpy ndarray or torch Tensor
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
    Lazy-loaded on first request to optimise server startup time.
    """
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    settings = get_settings()
    model_name = settings.EMBEDDING_MODEL_NAME

    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading SentenceTransformers embedding model: {model_name}...")
        base_model = SentenceTransformer(model_name)
        _embedding_model = SafeEmbedder(base_model)
        logger.info("SentenceTransformers model loaded and wrapped in SafeEmbedder.")
        return _embedding_model
    except Exception as e:
        logger.error(f"Failed to load embedding model '{model_name}': {str(e)}")

        class FallbackEmbedder:
            def encode(self, texts: List[str], **kwargs) -> List[List[float]]:
                return [[0.0] * 384 for _ in texts]

        _embedding_model = FallbackEmbedder()
        return _embedding_model
