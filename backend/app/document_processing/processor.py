from dataclasses import dataclass
from typing import List, Dict, Any, Union, Optional

from .pdf_extractor import PDFExtractor, ExtractedPage
from .cleaner import TextCleaner
from .section_detector import SectionDetector
from .chunker import DocumentChunker, DocumentChunk
from .ocr_extension import OCRExtensionHook
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class ProcessingResult:
    document_id: str
    user_id: str
    file_name: str
    company_name: str
    financial_year: str
    total_pages: int
    non_empty_pages: int
    scanned_pages: int
    total_chunks: int
    pages: List[ExtractedPage]
    chunks: List[DocumentChunk]


class DocumentProcessor:
    """
    Main orchestrator pipeline class for Python PDF document processing:
    PDF → page extraction → text cleaning → section detection → chunking → metadata creation.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        ocr_hook: Optional[OCRExtensionHook] = None,
    ):
        self.extractor = PDFExtractor(ocr_hook=ocr_hook)
        self.cleaner = TextCleaner()
        self.section_detector = SectionDetector()
        self.chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def process_pdf(
        self,
        pdf_source: Union[bytes, str],
        document_id: str,
        user_id: str,
        file_name: str = "document.pdf",
        company_name: str = "Unknown Company",
        financial_year: str = "FY2024",
    ) -> ProcessingResult:
        """
        Runs the complete PDF processing pipeline:
        1. Extract text page-by-page (preserving 1-indexed page numbers).
        2. Detect empty and scanned pages.
        3. Clean text per page while preserving financial figures and headings.
        4. Detect financial sections statefully.
        5. Generate semantic chunks with complete metadata attached.
        """
        logger.info(f"DocumentProcessor: Processing PDF for document_id='{document_id}', user_id='{user_id}'.")

        # 1. Page Extraction
        pages = self.extractor.extract(pdf_source)
        total_pages = len(pages)
        non_empty_pages = sum(1 for p in pages if not p.is_empty)
        scanned_pages = sum(1 for p in pages if p.is_scanned)

        # 2. Chunking & Metadata Generation
        chunks = self.chunker.chunk_pages(
            pages=pages,
            document_id=document_id,
            user_id=user_id,
            file_name=file_name,
            company_name=company_name,
            financial_year=financial_year,
        )

        logger.info(
            f"DocumentProcessor complete: {total_pages} total pages ({non_empty_pages} non-empty, "
            f"{scanned_pages} scanned) -> {len(chunks)} chunks created."
        )

        return ProcessingResult(
            document_id=document_id,
            user_id=user_id,
            file_name=file_name,
            company_name=company_name,
            financial_year=financial_year,
            total_pages=total_pages,
            non_empty_pages=non_empty_pages,
            scanned_pages=scanned_pages,
            total_chunks=len(chunks),
            pages=pages,
            chunks=chunks,
        )
