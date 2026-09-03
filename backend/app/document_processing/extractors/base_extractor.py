from abc import ABC, abstractmethod
from typing import Optional, Callable
from ..models import ExtractedDocument


class BaseDocumentExtractor(ABC):
    """
    Abstract Base Class for format-specific financial document extractors.
    All format extractors must normalize output into `ExtractedDocument`.
    """

    @abstractmethod
    def extract(
        self,
        file_bytes: bytes,
        document_id: str,
        filename: str,
        user_id: Optional[str] = None,
        company_name: Optional[str] = None,
        financial_year: Optional[str] = None,
        on_progress: Optional[Callable[[str, int, str], None]] = None,
    ) -> ExtractedDocument:
        """
        Extracts document contents and normalizes into ExtractedDocument.
        """
        pass
