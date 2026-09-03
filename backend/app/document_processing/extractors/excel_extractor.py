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


class ExcelExtractor(BaseDocumentExtractor):
    """
    Extracts structured financial spreadsheets (XLSX, XLS).
    Preserves sheets, cell coordinates, financial tables, headers, and formulas.
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
        ext = filename.lower().split(".")[-1]

        if on_progress:
            on_progress("Reading spreadsheets", 25, f"Reading Excel sheets from {filename}")

        sheets_data = []
        if ext == "xls":
            sheets_data = self._read_xls(file_bytes)
        else:
            sheets_data = self._read_xlsx(file_bytes)

        if not sheets_data:
            # Fallback using pandas
            sheets_data = self._read_pandas_fallback(file_bytes)

        doc_sections: List[DocumentSection] = []
        detected_company = company_name
        detected_year = financial_year
        detected_currency = None
        detected_units = None

        total_sheets = len(sheets_data)
        for s_idx, sheet_info in enumerate(sheets_data, 1):
            sheet_name = sheet_info["name"]
            rows: List[List[Any]] = sheet_info["rows"]

            if on_progress:
                pct = int(35 + (s_idx / max(total_sheets, 1)) * 40)
                on_progress("Processing sheets", pct, f'Extracting sheet "{sheet_name}"')

            # Clean rows: filter out completely empty rows
            cleaned_rows = []
            for r_idx, row in enumerate(rows, 1):
                str_cells = [str(c).strip() if c is not None else "" for c in row]
                if any(str_cells):
                    cleaned_rows.append((r_idx, str_cells))

            if not cleaned_rows:
                continue

            # Scan top rows for metadata (company name, FY, units, currency)
            for _, str_cells in cleaned_rows[:8]:
                row_text = " ".join(str_cells)
                if not detected_company:
                    m_comp = re.search(r"([A-Z][A-Za-z0-9\s,&]+?(?:Limited|Ltd\.?|Corporation|Corp\.?|Inc\.?|LLC|Pvt|Bank))(?:\s*[-–(]|\s+Consolidated|\s*$)", row_text, re.IGNORECASE)
                    if m_comp:
                        detected_company = m_comp.group(1).strip()
                if not detected_year:
                    m_fy = re.search(r"(FY\s*20\d\d|20\d\d\s*-\s*20\d\d|Year\s*ended.*?20\d\d)", row_text, re.IGNORECASE)
                    if m_fy:
                        detected_year = m_fy.group(0).strip()
                if not detected_currency:
                    m_curr = re.search(r"(\$|USD|INR|₹|EUR|€|GBP|£|Rs\.?)", row_text, re.IGNORECASE)
                    if m_curr:
                        detected_currency = m_curr.group(1).strip()
                if not detected_units:
                    m_unit = re.search(r"(in\s+crores?|in\s+lakhs?|in\s+millions?|in\s+billions?|in\s+thousands?)", row_text, re.IGNORECASE)
                    if m_unit:
                        detected_units = m_unit.group(1).strip()

            # Group rows into structured tabular blocks (batches of up to 40 rows)
            batch_size = 35
            blocks: List[DocumentBlock] = []
            extracted_tables: List[ExtractedTable] = []

            # First row or headers
            header_row = cleaned_rows[0][1] if cleaned_rows else []
            data_rows = cleaned_rows[1:] if len(cleaned_rows) > 1 else cleaned_rows

            for i in range(0, len(data_rows), batch_size):
                chunk_slice = data_rows[i : i + batch_size]
                if not chunk_slice:
                    continue

                r_start = chunk_slice[0][0]
                r_end = chunk_slice[-1][0]
                row_range_str = f"{r_start}–{r_end}"
                human_lbl = f'Sheet "{sheet_name}", rows {row_range_str}'

                loc = SourceLocation(
                    format_type="xlsx" if ext != "xls" else "xls",
                    sheet_name=sheet_name,
                    row_range=row_range_str,
                    section_name=sheet_name,
                    human_label=human_lbl
                )

                table_rows = [r[1] for r in chunk_slice]
                table_id = f"tbl_{sheet_name.lower().replace(' ', '_')}_{r_start}_{r_end}"
                
                ext_table = ExtractedTable(
                    table_id=table_id,
                    headers=header_row,
                    rows=table_rows,
                    title=f'{sheet_name} (Rows {row_range_str})',
                    source_location=loc,
                    units=detected_units,
                    currency=detected_currency,
                    table_type="financial_sheet"
                )
                tbl_md = ext_table.to_markdown()
                extracted_tables.append(ext_table)

                blocks.append(DocumentBlock(
                    block_type="table",
                    content=tbl_md,
                    table=ext_table,
                    source_location=loc,
                    section=sheet_name
                ))

            sec_loc = SourceLocation(
                format_type="xlsx" if ext != "xls" else "xls",
                sheet_name=sheet_name,
                section_name=sheet_name,
                human_label=f'Sheet "{sheet_name}"'
            )

            raw_sheet_text = "\n\n".join([b.content for b in blocks])
            doc_section = DocumentSection(
                section_name=sheet_name,
                source_location=sec_loc,
                blocks=blocks,
                raw_text=raw_sheet_text,
                tables=extracted_tables,
                metadata={"total_rows": len(cleaned_rows), "sheet_name": sheet_name}
            )
            doc_sections.append(doc_section)

        return ExtractedDocument(
            document_id=document_id,
            file_name=filename,
            file_type="xls" if ext == "xls" else "xlsx",
            file_size=len(file_bytes),
            doc_hash=doc_hash,
            company_name=detected_company,
            financial_year=detected_year,
            currency=detected_currency,
            units=detected_units,
            sections=doc_sections,
            pages_or_sheets_count=len(doc_sections),
            metadata={"sheets_count": len(doc_sections)}
        )

    def _read_xlsx(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """Reads XLSX using openpyxl."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
            sheets = []
            for name in wb.sheetnames:
                ws = wb[name]
                rows = []
                for row in ws.iter_rows(values_only=True):
                    rows.append(list(row))
                sheets.append({"name": name, "rows": rows})
            wb.close()
            return sheets
        except Exception as e:
            logger.warning(f"openpyxl failed to read XLSX: {str(e)}")
            return []

    def _read_xls(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """Reads legacy XLS using xlrd."""
        try:
            import xlrd
            wb = xlrd.open_workbook(file_contents=file_bytes)
            sheets = []
            for sheet_name in wb.sheet_names():
                sh = wb.sheet_by_name(sheet_name)
                rows = []
                for r in range(sh.nrows):
                    rows.append([sh.cell_value(r, c) for c in range(sh.ncols)])
                sheets.append({"name": sheet_name, "rows": rows})
            return sheets
        except Exception as e:
            logger.warning(f"xlrd failed to read XLS: {str(e)}")
            return []

    def _read_pandas_fallback(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """Reads spreadsheet using pandas."""
        try:
            import pandas as pd
            xls = pd.ExcelFile(io.BytesIO(file_bytes))
            sheets = []
            for sname in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sname)
                header = list(df.columns)
                rows = [header] + df.values.tolist()
                sheets.append({"name": sname, "rows": rows})
            return sheets
        except Exception as e:
            logger.warning(f"Pandas fallback failed to read Excel: {str(e)}")
            return []
