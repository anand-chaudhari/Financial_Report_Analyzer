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

            # Page count cap protection
            from ..config import get_settings
            settings = get_settings()
            max_pages = getattr(settings, "MAX_PDF_PAGES", 150)
            if len(doc) > max_pages:
                raise ValueError(f"PDF page count ({len(doc)}) exceeds the maximum allowed limit of {max_pages} pages.")

            # 1. First pass: extract text and tables
            page_data = []
            scanned_count = 0

            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_num = page_idx + 1

                # A. Native text
                text = page.get_text("text") or ""

                # B. Fast Table extraction into Markdown (only when table structures or delimiters are present)
                if "\t" in text or "   " in text or "|" in text:
                    try:
                        tabs = page.find_tables()
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
                                text = f"{text}\n\n" + "\n\n".join(table_mds)
                    except Exception:
                        pass

                # C. Layout blocks fallback if text is sparse
                if len(text.strip()) < 30:
                    blocks = page.get_text("blocks") or []
                    block_texts = [b[4] for b in blocks if len(b) > 4 and isinstance(b[4], str) and b[4].strip()]
                    if block_texts:
                        text = "\n\n".join(block_texts)

                images = page.get_images() or []
                image_count = len(images)
                is_scanned = len(text.strip()) < 40 and image_count > 0

                if is_scanned:
                    scanned_count += 1

                page_data.append({
                    "page_number": page_num,
                    "page_obj": page,
                    "text": text,
                    "image_count": image_count,
                    "is_scanned": is_scanned,
                })

            # 2. Only run OCR transcription if the overwhelming majority (>= 65%) of pages are scanned images
            scanned_ratio = (scanned_count / len(doc)) if len(doc) > 0 else 0
            if scanned_ratio >= 0.65 and scanned_count >= 3:
                logger.info(f"Detected scanned PDF ({scanned_count}/{len(doc)} pages, {scanned_ratio*100:.1f}%). Performing Gemini vision transcription...")
                try:
                    from ..config import get_settings
                    settings = get_settings()
                    if settings.GEMINI_API_KEY:
                        import google.generativeai as genai
                        import tempfile
                        import re
                        import os
                        genai.configure(api_key=settings.GEMINI_API_KEY)

                        temp_pdf_path = None
                        if isinstance(pdf_source, bytes):
                            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
                                tf.write(pdf_source)
                                temp_pdf_path = tf.name
                            source_path = temp_pdf_path
                        else:
                            source_path = str(pdf_source)

                        uploaded_file = genai.upload_file(path=source_path, mime_type="application/pdf")
                        
                        prompt = (
                            "Transcribe all text, financial tables, balance sheets, profit and loss statements, "
                            "operating revenues, expenses, profit figures, and accounting notes page by page. "
                            "Format tables as clean Markdown tables with exact figures. "
                            "Format output strictly with page delimiters: '=== PAGE {X} ===' before each page's content, "
                            "where {X} is the 1-indexed page number (e.g. === PAGE 1 ===, === PAGE 2 ===)."
                        )

                        for m_name in ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]:
                            try:
                                v_model = genai.GenerativeModel(model_name=m_name)
                                res = v_model.generate_content([uploaded_file, prompt])
                                if res and res.text:
                                    page_splits = re.split(r"===\s*PAGE\s*(\d+)\s*===", res.text, flags=re.IGNORECASE)
                                    if len(page_splits) > 1:
                                        for i in range(1, len(page_splits), 2):
                                            p_num = int(page_splits[i])
                                            p_text = page_splits[i+1].strip() if i+1 < len(page_splits) else ""
                                            if 1 <= p_num <= len(page_data) and p_text:
                                                page_data[p_num - 1]["text"] = p_text
                                                page_data[p_num - 1]["is_scanned"] = False
                                        logger.info(f"Single-pass Gemini transcription completed for {len(doc)} pages.")
                                        break
                            except Exception as m_err:
                                logger.debug(f"Gemini model '{m_name}' note: {str(m_err)}")

                        if temp_pdf_path and os.path.exists(temp_pdf_path):
                            try:
                                os.remove(temp_pdf_path)
                            except Exception:
                                pass
                except Exception as doc_ocr_err:
                    logger.warning(f"Single-pass document transcription note: {str(doc_ocr_err)}")

            # 3. Build ExtractedPage models
            for pd in page_data:
                txt = pd["text"]
                has_tables = "\t" in txt or "   " in txt or "|" in txt
                extracted_pages.append(
                    ExtractedPage(
                        page_number=pd["page_number"],
                        raw_text=txt,
                        char_count=len(txt),
                        image_count=pd["image_count"],
                        is_empty=not txt.strip(),
                        is_scanned=pd["is_scanned"],
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
