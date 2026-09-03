from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class SourceLocation:
    """
    Precise source location within a financial document.
    Examples:
    - PDF: Page 42
    - Excel: Sheet "Profit & Loss", rows 10–18
    - DOCX: Section "Revenue"
    - CSV: Rows 1–25
    - Markdown / Text: Section "Risk Factors" or Lines 1–40
    - JSON: Node "financials.balance_sheet"
    """
    format_type: str = "pdf"  # pdf, xlsx, xls, csv, docx, txt, md, json
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    row_range: Optional[str] = None
    section_name: Optional[str] = None
    node_path: Optional[str] = None
    human_label: str = ""

    def get_citation_label(self) -> str:
        """Returns a standardized human-readable citation label for LLM responses."""
        if self.human_label:
            return self.human_label

        if self.format_type == "pdf" and self.page_number:
            return f"Page {self.page_number}"
        elif self.format_type in ("xlsx", "xls") and self.sheet_name:
            if self.row_range:
                return f'Sheet "{self.sheet_name}", rows {self.row_range}'
            return f'Sheet "{self.sheet_name}"'
        elif self.format_type == "csv":
            if self.row_range:
                return f"CSV Rows {self.row_range}"
            return "CSV Data"
        elif self.format_type == "docx" and self.section_name:
            return f'Section "{self.section_name}"'
        elif self.format_type in ("md", "txt") and self.section_name:
            return f'Section "{self.section_name}"'
        elif self.format_type == "json" and self.node_path:
            return f'JSON "{self.node_path}"'

        if self.page_number:
            return f"Page {self.page_number}"
        if self.section_name:
            return f'Section "{self.section_name}"'
        return "Document"


@dataclass
class ExtractedTable:
    """
    Structured representation of a financial table preserving headers, rows, units and currency.
    """
    table_id: str
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    markdown: str = ""
    title: Optional[str] = None
    source_location: SourceLocation = field(default_factory=SourceLocation)
    units: Optional[str] = None
    currency: Optional[str] = None
    table_type: str = "financial_statement"  # balance_sheet, income_statement, cash_flow, notes, generic

    def to_markdown(self) -> str:
        """Converts table data to a clean, well-aligned Markdown table string."""
        if self.markdown:
            return self.markdown

        if not self.headers and not self.rows:
            return ""

        headers = self.headers if self.headers else [f"Col {i+1}" for i in range(len(self.rows[0])) if self.rows]
        header_line = "| " + " | ".join(str(h).replace("\n", " ").strip() for h in headers) + " |"
        sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"

        row_lines = []
        for row in self.rows:
            # Pad or truncate row to header length
            padded_row = list(row) + [""] * (len(headers) - len(row))
            formatted_cells = [str(c).replace("\n", " ").strip() for c in padded_row[:len(headers)]]
            row_lines.append("| " + " | ".join(formatted_cells) + " |")

        table_md = "\n".join([header_line, sep_line] + row_lines)
        if self.title:
            table_md = f"### {self.title}\n" + table_md
        self.markdown = table_md
        return table_md


@dataclass
class DocumentBlock:
    """
    A discrete block of document content (paragraph, heading, structured table, or key-value list).
    """
    block_type: str  # text, table, heading, key_value, code
    content: str
    table: Optional[ExtractedTable] = None
    source_location: SourceLocation = field(default_factory=SourceLocation)
    section: str = "General"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentSection:
    """
    A logical section, page, or worksheet within the document.
    """
    section_name: str
    source_location: SourceLocation
    blocks: List[DocumentBlock] = field(default_factory=list)
    raw_text: str = ""
    tables: List[ExtractedTable] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedDocument:
    """
    Normalized internal document representation across all supported formats (PDF, XLSX, XLS, CSV, DOCX, TXT, MD, JSON).
    """
    document_id: str
    file_name: str
    file_type: str  # pdf, xlsx, xls, csv, docx, txt, md, json
    file_size: int
    doc_hash: str
    company_name: Optional[str] = None
    financial_year: Optional[str] = None
    currency: Optional[str] = None
    units: Optional[str] = None
    sections: List[DocumentSection] = field(default_factory=list)
    pages_or_sheets_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


# Backward-compatible page model used by existing PDF and cleaner code
@dataclass
class ExtractedPage:
    page_number: int
    text: str
    tables: List[Dict[str, Any]] = field(default_factory=list)
    is_scanned: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
