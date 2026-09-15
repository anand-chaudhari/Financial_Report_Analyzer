import hashlib
from typing import Optional, Callable, List, Union, Any
from .base_extractor import BaseDocumentExtractor
from ..models import (
    ExtractedDocument,
    DocumentSection,
    DocumentBlock,
    ExtractedTable,
    SourceLocation,
    ExtractedPage,
)
from ..pdf_extractor import PDFExtractor
from ..section_detector import SectionDetector
from ...utils.logger import setup_logger

logger = setup_logger(__name__)


class PDFExtractorAdapter(BaseDocumentExtractor):
    """
    Adapts the high-performance parallel PDFExtractor into the normalized ExtractedDocument model.
    """

    def __init__(self):
        self.raw_pdf_extractor = PDFExtractor()

    def extract(
        self,
        file_bytes: Union[bytes, str],
        document_id: str,
        filename: str,
        user_id: Optional[str] = None,
        company_name: Optional[str] = None,
        financial_year: Optional[str] = None,
        on_progress: Optional[Callable[[str, int, str], None]] = None,
        cancellation_token: Optional[Any] = None,
    ) -> ExtractedDocument:
        import os
        if isinstance(file_bytes, str):
            # For path-based inputs, read a representative 128 KB sample for the hash
            # rather than loading the entire (potentially large) PDF into RAM.
            doc_hash = ""
            if os.path.exists(file_bytes):
                hasher = hashlib.sha256()
                file_size_bytes = os.path.getsize(file_bytes)
                # Include file size in hash so that two files with identical first 128 KB
                # but different lengths get different hashes.
                hasher.update(str(file_size_bytes).encode())
                with open(file_bytes, "rb") as f:
                    # First 64 KB
                    hasher.update(f.read(65536))
                    # Last 64 KB (if file is large enough)
                    if file_size_bytes > 131072:
                        f.seek(-65536, 2)
                        hasher.update(f.read(65536))
                doc_hash = hasher.hexdigest()
        else:
            doc_hash = hashlib.sha256(file_bytes).hexdigest()

        # Use our optimized parallel PDF extractor with pre-flight inspection and batching
        pages: List[ExtractedPage] = self.raw_pdf_extractor.extract(
            file_bytes,
            on_progress=on_progress,
            cancellation_token=cancellation_token,
        )
        
        # Detect sections across pages statefully
        detector = SectionDetector()

        if on_progress:
            on_progress("Extracting tables", 35, "Preserving financial statement tables and layout")

        doc_sections: List[DocumentSection] = []

        for p in pages:
            page_no = p.page_number
            page_text = getattr(p, 'raw_text', getattr(p, 'text', '')) or ''
            sec_name = detector.update_and_get_section(page_text)
            loc = SourceLocation(
                format_type="pdf",
                page_number=page_no,
                section_name=sec_name,
                human_label=f"Page {page_no}"
            )

            blocks: List[DocumentBlock] = []
            extracted_tables: List[ExtractedTable] = []

            # 1. Add structured tables
            p_tables = getattr(p, 'tables', []) or []
            for idx, tbl_data in enumerate(p_tables):
                t_id = f"tbl_p{page_no}_{idx+1}"
                t_headers = tbl_data.get("headers", []) if isinstance(tbl_data, dict) else []
                t_rows = tbl_data.get("rows", []) if isinstance(tbl_data, dict) else []
                t_md = tbl_data.get("markdown", "") if isinstance(tbl_data, dict) else ""
                
                ext_table = ExtractedTable(
                    table_id=t_id,
                    headers=t_headers,
                    rows=t_rows,
                    markdown=t_md,
                    source_location=loc,
                    table_type="financial_statement"
                )
                if not ext_table.markdown and (t_headers or t_rows):
                    ext_table.to_markdown()

                extracted_tables.append(ext_table)
                blocks.append(DocumentBlock(
                    block_type="table",
                    content=ext_table.markdown,
                    table=ext_table,
                    source_location=loc,
                    section=sec_name
                ))

            # 2. Add text content
            if page_text:
                blocks.append(DocumentBlock(
                    block_type="text",
                    content=page_text,
                    source_location=loc,
                    section=sec_name
                ))

            doc_section = DocumentSection(
                section_name=sec_name,
                source_location=loc,
                blocks=blocks,
                raw_text=page_text,
                tables=extracted_tables,
                metadata={"is_scanned": getattr(p, 'is_scanned', False)}
            )
            doc_sections.append(doc_section)

        return ExtractedDocument(
            document_id=document_id,
            file_name=filename,
            file_type="pdf",
            file_size=len(file_bytes),
            doc_hash=doc_hash,
            company_name=company_name,
            financial_year=financial_year,
            sections=doc_sections,
            pages_or_sheets_count=len(pages),
            metadata={"total_pages": len(pages)}
        )
