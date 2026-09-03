import io
import re
import hashlib
from typing import Optional, Callable, List, Dict, Any
from .base_extractor import BaseDocumentExtractor
from ..models import (
    ExtractedDocument,
    DocumentSection,
    DocumentBlock,
    ExtractedTable,
    SourceLocation,
)
from ...utils.logger import setup_logger

logger = setup_logger(__name__)


class DocxExtractor(BaseDocumentExtractor):
    """
    Extracts DOCX documents while preserving heading hierarchy, paragraphs, and structured Word tables.
    """

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
        doc_hash = hashlib.sha256(file_bytes).hexdigest()

        if on_progress:
            on_progress("Reading Word Document", 25, f"Extracting headings, text and tables from {filename}")

        import docx

        doc = docx.Document(io.BytesIO(file_bytes))

        # We will parse elements sequentially by examining body elements
        current_section = "Executive Summary"
        sections_map: Dict[str, List[DocumentBlock]] = {current_section: []}
        sections_tables: Dict[str, List[ExtractedTable]] = {current_section: []}

        detected_company = company_name
        detected_year = financial_year
        detected_currency = None
        detected_units = None

        # 1. Iterate over paragraphs
        for p_idx, p in enumerate(doc.paragraphs):
            text = p.text.strip()
            if not text:
                continue

            style_name = p.style.name.lower() if p.style and p.style.name else ""
            is_heading = "heading" in style_name or "title" in style_name

            if is_heading:
                current_section = text
                if current_section not in sections_map:
                    sections_map[current_section] = []
                    sections_tables[current_section] = []

            # Detect company / year / units metadata
            if not detected_company:
                m_comp = re.search(r"([A-Z][A-Za-z0-9\s,&.-]+(?:Limited|Ltd|Corporation|Corp|Inc|LLC|Pvt|Bank))", text, re.IGNORECASE)
                if m_comp:
                    detected_company = m_comp.group(1).strip()
            if not detected_year:
                m_fy = re.search(r"(FY\s*20\d\d|20\d\d\s*-\s*20\d\d|20\d\d)", text, re.IGNORECASE)
                if m_fy:
                    detected_year = m_fy.group(0).strip()

            loc = SourceLocation(
                format_type="docx",
                section_name=current_section,
                human_label=f'Section "{current_section}"'
            )

            sections_map[current_section].append(DocumentBlock(
                block_type="heading" if is_heading else "text",
                content=text,
                source_location=loc,
                section=current_section
            ))

        # 2. Iterate over tables
        for t_idx, tbl in enumerate(doc.tables, 1):
            table_rows: List[List[str]] = []
            for row in tbl.rows:
                row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                table_rows.append(row_cells)

            if not table_rows:
                continue

            headers = table_rows[0]
            data_rows = table_rows[1:] if len(table_rows) > 1 else []

            loc = SourceLocation(
                format_type="docx",
                section_name=current_section,
                human_label=f'Section "{current_section}", Table {t_idx}'
            )

            ext_table = ExtractedTable(
                table_id=f"tbl_docx_{t_idx}",
                headers=headers,
                rows=data_rows,
                title=f"Table {t_idx} ({current_section})",
                source_location=loc,
                units=detected_units,
                currency=detected_currency,
                table_type="financial_table"
            )
            tbl_md = ext_table.to_markdown()

            if current_section not in sections_map:
                sections_map[current_section] = []
                sections_tables[current_section] = []

            sections_tables[current_section].append(ext_table)
            sections_map[current_section].append(DocumentBlock(
                block_type="table",
                content=tbl_md,
                table=ext_table,
                source_location=loc,
                section=current_section
            ))

        # Build DocumentSection list
        doc_sections: List[DocumentSection] = []
        for sec_name, blks in sections_map.items():
            if not blks:
                continue
            loc = SourceLocation(
                format_type="docx",
                section_name=sec_name,
                human_label=f'Section "{sec_name}"'
            )
            raw_text = "\n\n".join([b.content for b in blks])
            doc_sections.append(DocumentSection(
                section_name=sec_name,
                source_location=loc,
                blocks=blks,
                raw_text=raw_text,
                tables=sections_tables.get(sec_name, []),
                metadata={"blocks_count": len(blks)}
            ))

        return ExtractedDocument(
            document_id=document_id,
            file_name=filename,
            file_type="docx",
            file_size=len(file_bytes),
            doc_hash=doc_hash,
            company_name=detected_company,
            financial_year=detected_year,
            currency=detected_currency,
            units=detected_units,
            sections=doc_sections,
            pages_or_sheets_count=len(doc_sections),
            metadata={"sections_count": len(doc_sections)}
        )
