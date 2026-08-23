from typing import Tuple, Optional, Any
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class OCRExtensionHook:
    """
    Extension point and handler for detecting empty or scanned/image-only PDF pages.
    Provides pluggable OCR execution hook interface.
    """

    def __init__(self, min_char_threshold: int = 40):
        self.min_char_threshold = min_char_threshold

    def inspect_page(
        self,
        raw_text: str,
        image_count: int = 0
    ) -> Tuple[bool, bool]:
        """
        Inspects page text length and embedded image count.
        Returns:
            (is_empty, is_scanned)
        """
        stripped_text = (raw_text or "").strip()
        char_count = len(stripped_text)

        is_empty = char_count == 0 and image_count == 0
        is_scanned = char_count < self.min_char_threshold and image_count > 0

        return is_empty, is_scanned

    def perform_ocr(self, page_object: Any) -> str:
        """
        Pluggable extension point for OCR.
        Can be wired to pytesseract, easyocr, or pdf2image if OCR engine is enabled.
        Returns extracted OCR text string.
        """
        logger.debug("OCRExtensionHook: OCR hook triggered for scanned page.")
        # OCR extension placeholder for external engines
        return ""
