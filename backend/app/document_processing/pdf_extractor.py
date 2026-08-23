import io
from dataclasses import dataclass
from typing import List, Union, Optional
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from .ocr_extension import OCRExtensionHook
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class ExtractedPage:
    page_number: int  # 1-indexed page number
    raw_text: str
    char_count: int
    image_count: int = 0
    is_empty: bool = False
    is_scanned: bool = False
    has_tables: bool = False


class PDFExtractor:
    """
    Page-by-page PDF text extraction using PyMuPDF (fitz).
    Preserves 1-indexed page numbers, counts images, and identifies empty/scanned pages.
    """

    def __init__(self, ocr_hook: Optional[OCRExtensionHook] = None):
        self.ocr_hook = ocr_hook or OCRExtensionHook()

    def extract(self, pdf_source: Union[bytes, str]) -> List[ExtractedPage]:
        extracted_pages: List[ExtractedPage] = []
        doc = None

        try:
            if isinstance(pdf_source, bytes):
                doc = fitz.open(stream=pdf_source, filetype="pdf")
            else:
                doc = fitz.open(pdf_source)

            logger.info(f"Opened PDF with {len(doc)} pages.")

            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_num = page_idx + 1  # 1-indexed page number

                text = page.get_text("text") or ""
                images = page.get_images() or []
                image_count = len(images)

                is_empty, is_scanned = self.ocr_hook.inspect_page(
                    raw_text=text,
                    image_count=image_count
                )

                # Execute OCR fallback if page is scanned/image-only
                if is_scanned and not text.strip():
                    ocr_text = self.ocr_hook.perform_ocr(page)
                    if ocr_text:
                        text = ocr_text

                has_tables = "\t" in text or "   " in text or "|" in text

                extracted_pages.append(
                    ExtractedPage(
                        page_number=page_num,
                        raw_text=text,
                        char_count=len(text),
                        image_count=image_count,
                        is_empty=is_empty,
                        is_scanned=is_scanned,
                        has_tables=has_tables,
                    )
                )

        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {str(e)}")
            raise e
        finally:
            if doc is not None:
                doc.close()

        return extracted_pages


def extract_text_from_pdf(pdf_source: Union[bytes, str]) -> List[ExtractedPage]:
    """Functional helper for PDF page extraction."""
    extractor = PDFExtractor()
    return extractor.extract(pdf_source)
