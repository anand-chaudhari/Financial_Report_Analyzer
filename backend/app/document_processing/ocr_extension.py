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
        Extracts text from a page object using layout blocks, table detection, or Gemini Vision OCR.
        """
        # 1. Try PyMuPDF table detection
        try:
            tabs = page_object.find_tables()
            if tabs and getattr(tabs, "tables", None) and len(tabs.tables) > 0:
                table_mds = []
                for tab in tabs:
                    df = tab.extract()
                    if df and len(df) > 0:
                        header = " | ".join(str(cell or "").strip().replace("\n", " ") for cell in df[0])
                        separator = " | ".join("---" for _ in df[0])
                        rows = [" | ".join(str(cell or "").strip().replace("\n", " ") for cell in row) for row in df[1:]]
                        table_md = f"| {header} |\n| {separator} |\n" + "\n".join(f"| {r} |" for r in rows)
                        table_mds.append(table_md)
                if table_mds:
                    table_text = "\n\n".join(table_mds)
                    raw = page_object.get_text("text") or ""
                    return f"{raw}\n\n{table_text}".strip()
        except Exception:
            pass

        # 2. Try layout blocks
        try:
            blocks = page_object.get_text("blocks")
            if blocks:
                block_texts = [b[4] for b in blocks if len(b) > 4 and isinstance(b[4], str) and b[4].strip()]
                if block_texts:
                    return "\n\n".join(block_texts)
        except Exception:
            pass

        # 3. Vision OCR via Gemini for scanned/image pages
        try:
            from ..config import get_settings
            settings = get_settings()
            if settings.GEMINI_API_KEY:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                
                pix = page_object.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                
                image_part = {
                    "mime_type": "image/png",
                    "data": img_bytes
                }
                
                prompt = (
                    "Transcribe all text, numbers, financial statements, balance sheet line items, "
                    "profit and loss figures, tables, and notes from this page image. "
                    "Format financial tables as clean Markdown tables with exact figures and currencies."
                )
                
                for m_name in ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]:
                    try:
                        v_model = genai.GenerativeModel(model_name=m_name)
                        res = v_model.generate_content([image_part, prompt])
                        if res and res.text:
                            return res.text.strip()
                    except Exception:
                        continue
        except Exception as ocr_err:
            logger.debug(f"Vision OCR note: {str(ocr_err)}")

        return ""
