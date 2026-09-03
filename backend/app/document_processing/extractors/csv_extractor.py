import csv
import io
import re
import hashlib
from typing import Optional, Callable, List
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


class CSVExtractor(BaseDocumentExtractor):
    """
    Extracts CSV and TSV financial files into structured markdown tables and sections.
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
            on_progress("Parsing CSV", 25, f"Detecting delimiter and parsing {filename}")

        # Decode content with UTF-8 / latin-1 fallback
        try:
            text_content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text_content = file_bytes.decode("latin-1", errors="ignore")

        # Detect delimiter
        sample = text_content[:4096]
        delimiter = ","
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            delimiter = dialect.delimiter
        except Exception:
            if "\t" in sample and sample.count("\t") > sample.count(","):
                delimiter = "\t"
            elif ";" in sample and sample.count(";") > sample.count(","):
                delimiter = ";"

        reader = csv.reader(io.StringIO(text_content), delimiter=delimiter)
        all_rows = [row for row in reader if any(c.strip() for c in row)]

        if not all_rows:
            all_rows = [["Empty CSV Document"]]

        header_row = all_rows[0]
        data_rows = all_rows[1:] if len(all_rows) > 1 else []

        detected_company = company_name
        detected_year = financial_year
        detected_currency = None
        detected_units = None

        # Inspect headers for financial metadata
        header_text = " ".join(header_row)
        if not detected_company:
            m_comp = re.search(r"([A-Z][A-Za-z0-9\s,&.-]+(?:Limited|Ltd|Corporation|Corp|Inc|LLC|Pvt|Bank))", header_text, re.IGNORECASE)
            if m_comp:
                detected_company = m_comp.group(1).strip()
        if not detected_year:
            m_fy = re.search(r"(FY\s*20\d\d|20\d\d\s*-\s*20\d\d|20\d\d)", header_text, re.IGNORECASE)
            if m_fy:
                detected_year = m_fy.group(0).strip()
        if not detected_currency:
            m_curr = re.search(r"(\$|USD|INR|₹|EUR|€|GBP|£|Rs\.?)", header_text, re.IGNORECASE)
            if m_curr:
                detected_currency = m_curr.group(1).strip()
        if not detected_units:
            m_unit = re.search(r"(in\s+crores?|in\s+lakhs?|in\s+millions?|in\s+billions?|in\s+thousands?)", header_text, re.IGNORECASE)
            if m_unit:
                detected_units = m_unit.group(1).strip()

        # Batch rows into chunks of 35 rows
        batch_size = 35
        blocks: List[DocumentBlock] = []
        extracted_tables: List[ExtractedTable] = []

        if not data_rows:
            # Only 1 header row
            loc = SourceLocation(format_type="csv", row_range="1", section_name="CSV Data", human_label="CSV Row 1")
            ext_table = ExtractedTable(
                table_id="tbl_csv_1",
                headers=header_row,
                rows=[],
                title="CSV Dataset",
                source_location=loc,
                units=detected_units,
                currency=detected_currency
            )
            extracted_tables.append(ext_table)
            blocks.append(DocumentBlock(block_type="table", content=ext_table.to_markdown(), table=ext_table, source_location=loc, section="CSV Data"))
        else:
            for i in range(0, len(data_rows), batch_size):
                chunk_slice = data_rows[i : i + batch_size]
                r_start = i + 2  # 1-indexed (after header)
                r_end = i + 1 + len(chunk_slice)
                row_range_str = f"{r_start}–{r_end}"
                human_lbl = f"CSV Rows {row_range_str}"

                loc = SourceLocation(
                    format_type="csv",
                    row_range=row_range_str,
                    section_name="CSV Data",
                    human_label=human_lbl
                )

                table_id = f"tbl_csv_{r_start}_{r_end}"
                ext_table = ExtractedTable(
                    table_id=table_id,
                    headers=header_row,
                    rows=chunk_slice,
                    title=f"Financial Data ({human_lbl})",
                    source_location=loc,
                    units=detected_units,
                    currency=detected_currency,
                    table_type="financial_data"
                )
                tbl_md = ext_table.to_markdown()
                extracted_tables.append(ext_table)

                blocks.append(DocumentBlock(
                    block_type="table",
                    content=tbl_md,
                    table=ext_table,
                    source_location=loc,
                    section="CSV Data"
                ))

        sec_loc = SourceLocation(
            format_type="csv",
            row_range=f"1–{len(all_rows)}",
            section_name="CSV Data",
            human_label="CSV Data"
        )

        doc_section = DocumentSection(
            section_name="CSV Data",
            source_location=sec_loc,
            blocks=blocks,
            raw_text="\n\n".join([b.content for b in blocks]),
            tables=extracted_tables,
            metadata={"total_rows": len(all_rows), "total_columns": len(header_row)}
        )

        return ExtractedDocument(
            document_id=document_id,
            file_name=filename,
            file_type="csv",
            file_size=len(file_bytes),
            doc_hash=doc_hash,
            company_name=detected_company,
            financial_year=detected_year,
            currency=detected_currency,
            units=detected_units,
            sections=[doc_section],
            pages_or_sheets_count=1,
            metadata={"total_rows": len(all_rows), "total_columns": len(header_row)}
        )
