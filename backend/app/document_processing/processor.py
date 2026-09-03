from dataclasses import dataclass, field
from typing import List, Dict, Any, Union, Optional, Callable

from .pdf_extractor import PDFExtractor, ExtractedPage
from .cleaner import TextCleaner
from .section_detector import SectionDetector
from .chunker import DocumentChunker, DocumentChunk
from .ocr_extension import OCRExtensionHook
from .file_detector import FileTypeDetector, UnsupportedFileFormatException
from .models import ExtractedDocument
from .extractors import (
    PDFExtractorAdapter,
    ExcelExtractor,
    CSVExtractor,
    DocxExtractor,
    TextMarkdownExtractor,
    JSONExtractor,
)
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
    pages: List[ExtractedPage] = field(default_factory=list)
    chunks: List[DocumentChunk] = field(default_factory=list)
    extracted_doc: Optional[ExtractedDocument] = None
    file_type: str = "pdf"
    currency: Optional[str] = None
    units: Optional[str] = None


class DocumentProcessor:
    """
    Main orchestrator pipeline class for Multi-Format Financial Document Processing:
    Supports PDF, XLSX, XLS, CSV, DOCX, TXT, MD, and JSON.
    Extracts structured content, preserves financial tables/metadata, normalizes to ExtractedDocument,
    and produces high-precision semantic vector chunks.
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
        
        # Format extractors registry
        self.pdf_extractor_adapter = PDFExtractorAdapter()
        self.excel_extractor = ExcelExtractor()
        self.csv_extractor = CSVExtractor()
        self.docx_extractor = DocxExtractor()
        self.text_md_extractor = TextMarkdownExtractor()
        self.json_extractor = JSONExtractor()

    def process_document(
        self,
        file_source: Union[bytes, str],
        document_id: str,
        user_id: str,
        file_name: str = "document.pdf",
        company_name: Optional[str] = None,
        financial_year: Optional[str] = None,
        mime_type: Optional[str] = None,
        on_stage_update: Optional[Callable[[str, int, Optional[str]], None]] = None,
    ) -> ProcessingResult:
        """
        Universal processing pipeline for any supported financial document format.
        Detects file type, dispatches to format-specific extractor, normalizes representation,
        and chunks into semantic financial blocks with exact source locations.
        """
        # 1. Detect and validate file format without reading full file into memory
        format_type, file_size = FileTypeDetector.validate_file(
            file_bytes_or_path=file_source,
            filename=file_name,
            mime_type=mime_type
        )

        logger.info(f"DocumentProcessor: Processing '{file_name}' as format '{format_type.upper()}' (ID: {document_id}, User: {user_id}, Size: {file_size / (1024*1024):.2f} MB).")

        # 2. Extract content using format-specific extractor
        extracted_doc: ExtractedDocument
        if format_type == "pdf":
            # Pass file_source directly (path or bytes) to prevent RAM ballooning on large PDFs
            extracted_doc = self.pdf_extractor_adapter.extract(
                file_bytes=file_source,
                document_id=document_id,
                filename=file_name,
                user_id=user_id,
                company_name=company_name,
                financial_year=financial_year,
                on_progress=on_stage_update
            )
        else:
            if isinstance(file_source, str):
                with open(file_source, "rb") as f:
                    file_bytes = f.read()
            else:
                file_bytes = file_source

            if on_stage_update:
                on_stage_update(
                    "Extracting",
                    25,
                    f"Extracting {format_type.upper()} tables and structure from '{file_name}'"
                )

            if format_type in ("xlsx", "xls"):
                extracted_doc = self.excel_extractor.extract(
                    file_bytes=file_bytes,
                    document_id=document_id,
                    filename=file_name,
                    user_id=user_id,
                    company_name=company_name,
                    financial_year=financial_year,
                    on_progress=on_stage_update
                )
            elif format_type == "csv":
                extracted_doc = self.csv_extractor.extract(
                    file_bytes=file_bytes,
                    document_id=document_id,
                    filename=file_name,
                    user_id=user_id,
                    company_name=company_name,
                    financial_year=financial_year,
                    on_progress=on_stage_update
                )
            elif format_type == "docx":
                extracted_doc = self.docx_extractor.extract(
                    file_bytes=file_bytes,
                    document_id=document_id,
                    filename=file_name,
                    user_id=user_id,
                    company_name=company_name,
                    financial_year=financial_year,
                    on_progress=on_stage_update
                )
            elif format_type in ("md", "txt"):
                extracted_doc = self.text_md_extractor.extract(
                    file_bytes=file_bytes,
                    document_id=document_id,
                    filename=file_name,
                    user_id=user_id,
                    company_name=company_name,
                    financial_year=financial_year,
                    on_progress=on_stage_update
                )
            elif format_type == "json":
                extracted_doc = self.json_extractor.extract(
                    file_bytes=file_bytes,
                    document_id=document_id,
                    filename=file_name,
                    user_id=user_id,
                    company_name=company_name,
                    financial_year=financial_year,
                    on_progress=on_stage_update
                )
            else:
                raise UnsupportedFileFormatException(f"Unsupported file format: {format_type}")

        # Stage: Chunking
        if on_stage_update:
            on_stage_update(
                "Chunking",
                65,
                f"Generating financial vector chunks preserving {format_type.upper()} table structure"
            )

        # 3. Chunk normalized document
        chunks = self.chunker.chunk_document(
            doc=extracted_doc,
            user_id=user_id,
        )

        final_company = extracted_doc.company_name or company_name or "Financial Report"
        final_year = extracted_doc.financial_year or financial_year or "FY2026"
        total_units = extracted_doc.pages_or_sheets_count
        non_empty_units = sum(1 for s in extracted_doc.sections if any(b.content.strip() for b in s.blocks) or (s.raw_text or "").strip())
        scanned_units = sum(1 for s in extracted_doc.sections if (s.metadata or {}).get("is_scanned"))

        logger.info(
            f"DocumentProcessor complete for '{file_name}' ({format_type.upper()}): "
            f"{total_units} section/pages/sheets ({non_empty_units} non-empty, {scanned_units} scanned) -> {len(chunks)} chunks created."
        )

        return ProcessingResult(
            document_id=document_id,
            user_id=user_id,
            file_name=file_name,
            company_name=final_company,
            financial_year=final_year,
            total_pages=total_units,
            non_empty_pages=non_empty_units,
            scanned_pages=scanned_units,
            total_chunks=len(chunks),
            chunks=chunks,
            extracted_doc=extracted_doc,
            file_type=format_type,
            currency=extracted_doc.currency,
            units=extracted_doc.units,
        )

    def process_pdf(
        self,
        pdf_source: Union[bytes, str],
        document_id: str,
        user_id: str,
        file_name: str = "document.pdf",
        company_name: str = "Unknown Company",
        financial_year: str = "FY2024",
        on_stage_update: Optional[Callable[[str, int, Optional[str]], None]] = None,
    ) -> ProcessingResult:
        """Backward-compatible process_pdf method."""
        return self.process_document(
            file_source=pdf_source,
            document_id=document_id,
            user_id=user_id,
            file_name=file_name,
            company_name=company_name,
            financial_year=financial_year,
            mime_type="application/pdf",
            on_stage_update=on_stage_update,
        )
