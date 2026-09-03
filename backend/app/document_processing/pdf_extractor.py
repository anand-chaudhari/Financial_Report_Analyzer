import io
import gc
import os
import concurrent.futures
from dataclasses import dataclass
from typing import List, Union, Optional, Dict, Any, Callable
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from .ocr_extension import OCRExtensionHook
from ..config import get_settings
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


def _extract_single_page_worker(doc_bytes_or_path: Union[bytes, str], page_idx: int) -> Dict[str, Any]:
    """
    Worker function executed in parallel to extract text, tables, and image metadata for a single page.
    """
    doc = None
    try:
        if isinstance(doc_bytes_or_path, bytes):
            doc = fitz.open(stream=doc_bytes_or_path, filetype="pdf")
        else:
            doc = fitz.open(doc_bytes_or_path)

        page = doc[page_idx]
        page_num = page_idx + 1

        # A. Extract native text
        text = page.get_text("text") or ""

        # B. Table extraction (only if table markers or multi-column tabs/spaces exist)
        has_table_delims = "\t" in text or "|" in text
        if not has_table_delims and "   " in text:
            # Check if there are numeric tabular data lines
            has_table_delims = any(
                sum(1 for char in line if char.isdigit()) >= 3 and "  " in line
                for line in text.split("\n")[:10]
            )

        if has_table_delims:
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

        return {
            "page_number": page_num,
            "text": text,
            "image_count": image_count,
            "is_scanned": is_scanned,
        }
    except Exception as e:
        logger.warning(f"Error extracting page {page_idx + 1}: {str(e)}")
        return {
            "page_number": page_idx + 1,
            "text": "",
            "image_count": 0,
            "is_scanned": False,
        }
    finally:
        if doc is not None:
            doc.close()


class PDFExtractor:
    """
    High-performance parallel PDF text extraction using PyMuPDF (fitz).
    Optimized for large files up to 200MB on localhost:
    - Pre-flight inspection of page count, text characteristics, and OCR requirements
    - Memory-bounded batch page extraction
    - Selective OCR only on verified scanned pages
    - Real-time stage progress reporting
    """

    def __init__(self, ocr_hook: Optional[OCRExtensionHook] = None):
        self.ocr_hook = ocr_hook or OCRExtensionHook()

    @staticmethod
    def inspect_pdf(pdf_source: Union[bytes, str]) -> Dict[str, Any]:
        """
        Pre-flight inspector: Checks page count, file size, text density, and whether OCR is required.
        Does not assume a large file requires OCR.
        """
        doc = None
        try:
            if isinstance(pdf_source, bytes):
                doc = fitz.open(stream=pdf_source, filetype="pdf")
                file_size = len(pdf_source)
            else:
                doc = fitz.open(pdf_source)
                file_size = os.path.getsize(pdf_source) if os.path.exists(pdf_source) else 0

            total_pages = len(doc)
            if total_pages == 0:
                return {
                    "total_pages": 0,
                    "file_size": file_size,
                    "ocr_required": False,
                    "classification": "empty",
                    "sample_chars_avg": 0,
                }

            # Sample pages across beginning, middle, and end (up to 8 pages)
            sample_indices = []
            if total_pages <= 6:
                sample_indices = list(range(total_pages))
            else:
                sample_indices = [0, 1, total_pages // 2, min(total_pages // 2 + 1, total_pages - 1), total_pages - 2, total_pages - 1]
                sample_indices = sorted(list(set(sample_indices)))

            total_sample_chars = 0
            scanned_sample_pages = 0
            for idx in sample_indices:
                try:
                    pg = doc[idx]
                    txt = pg.get_text("text") or ""
                    imgs = pg.get_images() or []
                    char_count = len(txt.strip())
                    total_sample_chars += char_count
                    if char_count < 40 and len(imgs) > 0:
                        scanned_sample_pages += 1
                except Exception:
                    pass

            avg_chars = total_sample_chars / max(len(sample_indices), 1)
            is_scanned = (scanned_sample_pages == len(sample_indices)) and avg_chars < 30
            is_mixed = scanned_sample_pages > 0 and not is_scanned

            if is_scanned:
                classification = "scanned_image"
                ocr_required = True
            elif is_mixed:
                classification = "mixed"
                ocr_required = True
            else:
                classification = "text_native"
                ocr_required = False

            report = {
                "total_pages": total_pages,
                "file_size": file_size,
                "ocr_required": ocr_required,
                "classification": classification,
                "sample_chars_avg": avg_chars,
                "sample_pages_inspected": len(sample_indices),
            }
            logger.info(
                f"PDF Pre-Flight Inspection: {total_pages} pages ({file_size / (1024*1024):.1f} MB) -> "
                f"Classification: '{classification}', Avg Chars/Page: {avg_chars:.0f}, OCR Required: {ocr_required}"
            )
            return report
        finally:
            if doc is not None:
                doc.close()

    def extract(
        self,
        pdf_source: Union[bytes, str],
        on_progress: Optional[Callable[[str, int, str], None]] = None,
        cancellation_token: Optional[Any] = None,
    ) -> List[ExtractedPage]:
        settings = get_settings()
        max_pages = getattr(settings, "MAX_PDF_PAGES", 2000)
        workers = getattr(settings, "PARALLEL_EXTRACTION_WORKERS", 8)
        workers = min(workers, os.cpu_count() or 4)

        # 1. Pre-flight Inspection
        if on_progress:
            on_progress("Analyzing", 15, "Inspecting document structure, page characteristics, and OCR requirements")

        inspection = self.inspect_pdf(pdf_source)
        total_pages = inspection["total_pages"]
        ocr_required = inspection["ocr_required"]
        classification = inspection["classification"]

        if total_pages > max_pages:
            raise ValueError(f"PDF page count ({total_pages}) exceeds the maximum allowed limit of {max_pages} pages.")

        if total_pages == 0:
            return []

        # 2. Extract pages in memory-controlled batches
        page_data: List[Dict[str, Any]] = [None] * total_pages
        PAGE_BATCH_SIZE = 25  # Controlled page batches for zero memory buildup

        for batch_start in range(0, total_pages, PAGE_BATCH_SIZE):
            if cancellation_token and getattr(cancellation_token, "is_set", lambda: False)():
                logger.info("PDF extraction cancelled by user.")
                raise InterruptedError("Document processing was cancelled.")

            batch_end = min(batch_start + PAGE_BATCH_SIZE, total_pages)
            pct = 20 + int((batch_start / total_pages) * 40)
            if on_progress:
                on_progress(
                    "Extracting",
                    pct,
                    f"Extracting native text and tables (Pages {batch_start + 1}–{batch_end} of {total_pages})"
                )

            batch_indices = list(range(batch_start, batch_end))
            if len(batch_indices) <= 2:
                for i in batch_indices:
                    page_data[i] = _extract_single_page_worker(pdf_source, i)
            else:
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    future_to_idx = {
                        executor.submit(_extract_single_page_worker, pdf_source, i): i
                        for i in batch_indices
                    }
                    for future in concurrent.futures.as_completed(future_to_idx):
                        idx = future_to_idx[future]
                        try:
                            page_data[idx] = future.result()
                        except Exception as exc:
                            logger.error(f"Page {idx + 1} extraction failed: {str(exc)}")
                            page_data[idx] = {
                                "page_number": idx + 1,
                                "text": "",
                                "image_count": 0,
                                "is_scanned": False,
                            }

            gc.collect()

        # 3. Targeted OCR on scanned image-only pages (only if text is actually missing)
        scanned_indices = [i for i, p in enumerate(page_data) if p and p["is_scanned"]]
        ocr_limit = getattr(settings, "OCR_MAX_PAGES", 50)

        if scanned_indices and settings.GEMINI_API_KEY:
            num_to_ocr = min(len(scanned_indices), ocr_limit)
            if on_progress:
                on_progress(
                    "OCR",
                    55,
                    f"Running selective OCR on {num_to_ocr} image-only page(s)"
                )
            logger.info(f"Running selective OCR on {num_to_ocr} scanned page(s)...")

            temp_doc = None
            try:
                if isinstance(pdf_source, bytes):
                    temp_doc = fitz.open(stream=pdf_source, filetype="pdf")
                else:
                    temp_doc = fitz.open(pdf_source)

                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)

                for idx in scanned_indices[:num_to_ocr]:
                    if cancellation_token and getattr(cancellation_token, "is_set", lambda: False)():
                        raise InterruptedError("Document processing was cancelled.")

                    try:
                        pg = temp_doc[idx]
                        pix = pg.get_pixmap(dpi=150)
                        img_bytes = pix.tobytes("png")
                        del pix  # Immediately free pixmap memory

                        image_part = {"mime_type": "image/png", "data": img_bytes}
                        prompt = (
                            "Transcribe all text, numbers, financial statements, balance sheet line items, "
                            "profit and loss figures, tables, and notes from this page image. "
                            "Format financial tables as clean Markdown tables with exact figures and currencies."
                        )

                        for m_name in ["gemini-2.0-flash", "gemini-1.5-flash"]:
                            try:
                                v_model = genai.GenerativeModel(model_name=m_name)
                                res = v_model.generate_content([image_part, prompt])
                                if res and res.text:
                                    page_data[idx]["text"] = res.text.strip()
                                    page_data[idx]["is_scanned"] = False
                                    break
                            except Exception:
                                continue
                    except Exception as ocr_err:
                        logger.debug(f"Targeted OCR error on page {idx + 1}: {str(ocr_err)}")
            finally:
                if temp_doc is not None:
                    temp_doc.close()

        # 4. Build ExtractedPage models
        extracted_pages: List[ExtractedPage] = []
        for pd in page_data:
            if not pd:
                continue
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

        gc.collect()
        return extracted_pages


def extract_text_from_pdf(
    pdf_source: Union[bytes, str],
    on_progress: Optional[Callable[[str, int, str], None]] = None,
) -> List[ExtractedPage]:
    """Functional helper for PDF page extraction."""
    extractor = PDFExtractor()
    return extractor.extract(pdf_source, on_progress=on_progress)
