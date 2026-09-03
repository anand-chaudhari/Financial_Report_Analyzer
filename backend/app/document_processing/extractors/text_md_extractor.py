import re
import hashlib
from typing import Optional, Callable, List, Dict
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


class TextMarkdownExtractor(BaseDocumentExtractor):
    """
    Extracts Plain Text (TXT) and Markdown (MD) financial documents.
    Preserves headings, sections, and structured Markdown tables.
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
        ext = "md" if filename.lower().endswith((".md", ".markdown")) else "txt"

        if on_progress:
            on_progress("Parsing text", 25, f"Extracting sections and markdown tables from {filename}")

        try:
            text_content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text_content = file_bytes.decode("latin-1", errors="ignore")

        lines = text_content.splitlines()

        current_section = "Overview"
        sections_map: Dict[str, List[DocumentBlock]] = {current_section: []}
        sections_tables: Dict[str, List[ExtractedTable]] = {current_section: []}

        detected_company = company_name
        detected_year = financial_year
        detected_currency = None
        detected_units = None

        idx = 0
        total_lines = len(lines)
        table_counter = 0

        while idx < total_lines:
            line = lines[idx]
            line_str = line.strip()

            if not line_str:
                idx += 1
                continue

            # 1. Check for Markdown Headings (# Header)
            m_h = re.match(r"^#{1,4}\s+(.+)$", line_str)
            if m_h:
                current_section = m_h.group(1).strip()
                if current_section not in sections_map:
                    sections_map[current_section] = []
                    sections_tables[current_section] = []
                idx += 1
                continue

            # 2. Check for Markdown Table (starts with |)
            if line_str.startswith("|") and "|" in line_str[1:]:
                table_lines = [line_str]
                idx += 1
                while idx < total_lines and lines[idx].strip().startswith("|"):
                    table_lines.append(lines[idx].strip())
                    idx += 1

                if len(table_lines) >= 2:
                    table_counter += 1
                    headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
                    raw_data_lines = table_lines[1:]
                    # Drop separator line (e.g. |---|---|)
                    if raw_data_lines and "---" in raw_data_lines[0]:
                        raw_data_lines = raw_data_lines[1:]

                    table_rows = []
                    for row_l in raw_data_lines:
                        cells = [c.strip() for c in row_l.strip("|").split("|")]
                        table_rows.append(cells)

                    loc = SourceLocation(
                        format_type=ext,
                        section_name=current_section,
                        human_label=f'Section "{current_section}", Table {table_counter}'
                    )

                    ext_table = ExtractedTable(
                        table_id=f"tbl_md_{table_counter}",
                        headers=headers,
                        rows=table_rows,
                        markdown="\n".join(table_lines),
                        source_location=loc,
                        table_type="financial_table"
                    )

                    if current_section not in sections_map:
                        sections_map[current_section] = []
                        sections_tables[current_section] = []

                    sections_tables[current_section].append(ext_table)
                    sections_map[current_section].append(DocumentBlock(
                        block_type="table",
                        content=ext_table.markdown,
                        table=ext_table,
                        source_location=loc,
                        section=current_section
                    ))
                    continue

            # 3. Regular text line or paragraph
            paragraph_lines = [line_str]
            idx += 1
            while idx < total_lines and lines[idx].strip() and not lines[idx].strip().startswith(("#", "|")):
                paragraph_lines.append(lines[idx].strip())
                idx += 1

            p_text = " ".join(paragraph_lines)

            # Metadata detection
            if not detected_company:
                m_comp = re.search(r"([A-Z][A-Za-z0-9\s,&.-]+(?:Limited|Ltd|Corporation|Corp|Inc|LLC|Pvt|Bank))", p_text, re.IGNORECASE)
                if m_comp:
                    detected_company = m_comp.group(1).strip()
            if not detected_year:
                m_fy = re.search(r"(FY\s*20\d\d|20\d\d\s*-\s*20\d\d|20\d\d)", p_text, re.IGNORECASE)
                if m_fy:
                    detected_year = m_fy.group(0).strip()

            loc = SourceLocation(
                format_type=ext,
                section_name=current_section,
                human_label=f'Section "{current_section}"'
            )

            if current_section not in sections_map:
                sections_map[current_section] = []
                sections_tables[current_section] = []

            sections_map[current_section].append(DocumentBlock(
                block_type="text",
                content=p_text,
                source_location=loc,
                section=current_section
            ))

        # Build DocumentSection list
        doc_sections: List[DocumentSection] = []
        for sec_name, blks in sections_map.items():
            if not blks:
                continue
            loc = SourceLocation(
                format_type=ext,
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
            file_type=ext,
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
