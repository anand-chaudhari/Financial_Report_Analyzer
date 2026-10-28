import os
import io
import gc
import re
import time
import concurrent.futures
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Union

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from ..config import get_settings
from ..utils.logger import setup_logger
from .ocr_extension import OCRExtensionHook

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
    unprocessed_ocr: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


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
        table_markdowns: List[str] = []
        has_table_delims = any(marker in text for marker in ["\t", "   ", "---", "|"])
        if has_table_delims:
            try:
                tabs = page.find_tables()
                if tabs and getattr(tabs, "tables", None) and len(tabs.tables) > 0:
                    table_mds = []
                    for t in tabs.tables:
                        try:
                            md = t.to_markdown()
                            if md and len(md.strip()) > 15:
                                table_mds.append(md.strip())
                        except Exception:
                            pass
                    if table_mds:
                        text = text + "\n\n" + "\n\n".join(table_mds)
                        table_markdowns = table_mds
            except Exception as tab_ex:
                logger.debug(f"find_tables note on page {page_num}: {str(tab_ex)}")

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
            "tables": table_markdowns,
        }
    except Exception as e:
        logger.warning(f"Error extracting page {page_idx + 1}: {str(e)}")
        return {
            "page_number": page_idx + 1,
            "text": "",
            "image_count": 0,
            "is_scanned": False,
            "tables": [],
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
    - Selective page-level OCR on verified image-only pages
    - Reports unprocessed OCR pages transparently without silent data loss
    - Real-time stage progress reporting
    """

    def __init__(self, ocr_hook: Optional[OCRExtensionHook] = None):
        self.ocr_hook = ocr_hook or OCRExtensionHook()

    @staticmethod
    def inspect_pdf(pdf_source: Union[bytes, str]) -> Dict[str, Any]:
        """
        Pre-flight inspector: Checks page count, file size, text density, and whether OCR is required.
        Intelligently differentiates text-native digital reports from scanned image PDFs.
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

            # Sample pages across beginning, middle, and end
            if total_pages <= 6:
                sample_indices = list(range(total_pages))
            else:
                sample_indices = sorted(list(set([
                    0,
                    1,
                    total_pages // 4,
                    total_pages // 2,
                    min(total_pages // 2 + 1, total_pages - 1),
                    (3 * total_pages) // 4,
                    total_pages - 2,
                    total_pages - 1
                ])))

            total_sample_chars = 0
            scanned_sample_pages = 0
            text_rich_pages = 0

            for idx in sample_indices:
                try:
                    pg = doc[idx]
                    txt = pg.get_text("text") or ""
                    imgs = pg.get_images() or []
                    char_count = len(txt.strip())
                    total_sample_chars += char_count
                    if char_count < 40 and len(imgs) > 0:
                        scanned_sample_pages += 1
                    if char_count >= 100:
                        text_rich_pages += 1
                except Exception:
                    pass

            num_samples = max(len(sample_indices), 1)
            avg_chars = total_sample_chars / num_samples

            is_scanned = (scanned_sample_pages == num_samples) and avg_chars < 30
            is_mixed = (
                not is_scanned
                and scanned_sample_pages >= max(2, int(num_samples * 0.5))
                and avg_chars < 150
                and text_rich_pages < max(1, int(num_samples * 0.4))
            )

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
        workers = min(workers, max(os.cpu_count() or 4, 4))

        file_size_bytes = len(pdf_source) if isinstance(pdf_source, bytes) else (
            os.path.getsize(pdf_source) if isinstance(pdf_source, str) and os.path.exists(pdf_source) else 0
        )
        if file_size_bytes > 50 * 1024 * 1024:   # > 50 MB
            workers = min(workers, 4)
        elif file_size_bytes > 20 * 1024 * 1024:  # > 20 MB
            workers = min(workers, 6)

        _PAGE_FUTURE_TIMEOUT_SEC: float = 15.0

        # 1. Pre-flight Inspection
        if on_progress:
            on_progress("Analyzing", 15, "Inspecting document structure, page characteristics, and OCR requirements")

        inspection = self.inspect_pdf(pdf_source)
        total_pages = inspection["total_pages"]
        avg_chars = inspection.get("sample_chars_avg", 0)

        if total_pages > max_pages:
            raise ValueError(f"PDF page count ({total_pages}) exceeds the maximum allowed limit of {max_pages} pages.")

        if total_pages == 0:
            return []

        # 2. Extract pages in memory-controlled batches
        page_data: List[Dict[str, Any]] = [None] * total_pages
        PAGE_BATCH_SIZE = 30  # Optimized batch size for throughput and memory efficiency

        for batch_start in range(0, total_pages, PAGE_BATCH_SIZE):
            if cancellation_token and getattr(cancellation_token, "is_set", lambda: False)():
                logger.info("PDF extraction cancelled by user.")
                raise InterruptedError("Document processing was cancelled.")

            batch_end = min(batch_start + PAGE_BATCH_SIZE, total_pages)
            pct = 20 + int((batch_start / total_pages) * 45)
            if on_progress:
                on_progress(
                    "Extracting",
                    pct,
                    f"Extracting native text and tables (Pages {batch_start + 1}–{batch_end} of {total_pages})"
                )

            batch_indices = list(range(batch_start, batch_end))
            if len(batch_indices) <= 2:
                for i in batch_indices:
                    try:
                        page_data[i] = _extract_single_page_worker(pdf_source, i)
                    except Exception as exc:
                        logger.warning(f"Page {i + 1} extraction failed (serial): {str(exc)}")
                        page_data[i] = {"page_number": i + 1, "text": "", "image_count": 0, "is_scanned": False, "tables": []}
            else:
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    future_to_idx = {
                        executor.submit(_extract_single_page_worker, pdf_source, i): i
                        for i in batch_indices
                    }
                    for future in concurrent.futures.as_completed(future_to_idx, timeout=_PAGE_FUTURE_TIMEOUT_SEC * len(batch_indices)):
                        idx = future_to_idx[future]
                        try:
                            page_data[idx] = future.result(timeout=_PAGE_FUTURE_TIMEOUT_SEC)
                        except concurrent.futures.TimeoutError:
                            logger.warning(
                                f"Page {idx + 1} extraction timed out after {_PAGE_FUTURE_TIMEOUT_SEC:.0f}s — skipping."
                            )
                            page_data[idx] = {"page_number": idx + 1, "text": "", "image_count": 0, "is_scanned": False, "tables": []}
                        except Exception as exc:
                            logger.error(f"Page {idx + 1} extraction failed: {str(exc)}")
                            page_data[idx] = {"page_number": idx + 1, "text": "", "image_count": 0, "is_scanned": False, "tables": []}

            for i in batch_indices:
                if page_data[i] is None:
                    page_data[i] = {"page_number": i + 1, "text": "", "image_count": 0, "is_scanned": False, "tables": []}

            gc.collect()

        # 3. Targeted Page-Level OCR ONLY on pages that genuinely lack native text
        scanned_indices = [
            i for i, p in enumerate(page_data)
            if p and p.get("is_scanned") and len(p.get("text", "").strip()) < 20
        ]

        if scanned_indices and settings.GEMINI_API_KEY:
            ocr_limit = max(15, getattr(settings, "OCR_MAX_PAGES", 15))
            num_to_ocr = min(len(scanned_indices), ocr_limit)
            unprocessed_indices = scanned_indices[num_to_ocr:]

            if num_to_ocr > 0:
                if on_progress:
                    on_progress(
                        "OCR",
                        55,
                        f"Running selective OCR on {num_to_ocr} image-only page(s)"
                    )
                logger.info(f"Running selective parallel OCR on {num_to_ocr} scanned page(s)...")

                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)

                def _ocr_single_page(idx: int) -> Optional[str]:
                    temp_doc = None
                    try:
                        if isinstance(pdf_source, bytes):
                            temp_doc = fitz.open(stream=pdf_source, filetype="pdf")
                        else:
                            temp_doc = fitz.open(pdf_source)
                        pg = temp_doc[idx]
                        pix = pg.get_pixmap(dpi=120)
                        img_bytes = pix.tobytes("jpeg")
                        del pix

                        image_part = {"mime_type": "image/jpeg", "data": img_bytes}
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
                                    return res.text.strip()
                            except Exception:
                                continue
                        return None
                    except Exception as ocr_err:
                        logger.debug(f"Targeted OCR error on page {idx + 1}: {str(ocr_err)}")
                        return None
                    finally:
                        if temp_doc is not None:
                            temp_doc.close()

                ocr_workers = min(4, os.cpu_count() or 4)
                with concurrent.futures.ThreadPoolExecutor(max_workers=ocr_workers) as ocr_executor:
                    ocr_futures = {
                        ocr_executor.submit(_ocr_single_page, idx): idx
                        for idx in scanned_indices[:num_to_ocr]
                    }
                    for fut in concurrent.futures.as_completed(ocr_futures, timeout=60.0):
                        idx = ocr_futures[fut]
                        try:
                            ocr_text = fut.result()
                            if ocr_text:
                                page_data[idx]["text"] = ocr_text
                                page_data[idx]["is_scanned"] = False
                        except Exception as e:
                            logger.debug(f"OCR future failed for page {idx + 1}: {str(e)}")

            if unprocessed_indices:
                unprocessed_page_nums = [idx + 1 for idx in unprocessed_indices]
                logger.warning(
                    f"OCR resource limit reached: {num_to_ocr} pages processed. "
                    f"Pages {unprocessed_page_nums} remain unprocessed for OCR."
                )
                for idx in unprocessed_indices:
                    if page_data[idx]:
                        page_data[idx]["unprocessed_ocr"] = True

        elif scanned_indices and not settings.GEMINI_API_KEY:
            logger.warning(f"Detected {len(scanned_indices)} scanned image pages, but GEMINI_API_KEY is not configured for OCR.")
            for idx in scanned_indices:
                if page_data[idx]:
                    page_data[idx]["unprocessed_ocr"] = True
        else:
            logger.info(
                f"PDF pre-flight confirmed text_native ({total_pages} pages, avg {avg_chars:.0f} chars/page). "
                "Skipping image OCR — native text extracted directly."
            )

        # 4. Build ExtractedPage models
        extracted_pages: List[ExtractedPage] = []
        for pd in page_data:
            if not pd:
                continue
            txt = pd["text"]
            has_tables = "\t" in txt or "   " in txt or "|" in txt or bool(pd.get("tables"))
            extracted_pages.append(
                ExtractedPage(
                    page_number=pd["page_number"],
                    raw_text=txt,
                    char_count=len(txt),
                    image_count=pd["image_count"],
                    is_empty=not txt.strip(),
                    is_scanned=pd.get("is_scanned", False),
                    has_tables=has_tables,
                    unprocessed_ocr=pd.get("unprocessed_ocr", False),
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
