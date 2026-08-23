import re
from typing import Optional, List, Tuple


class SectionDetector:
    """
    Detects standard financial report headings and SEC filing sections
    (e.g., Item 1, Item 1A, Item 7, Item 8, Balance Sheets, Cash Flows).
    Statefully tracks active section across document pages.
    """

    DEFAULT_SECTION = "General Information"

    SECTION_PATTERNS: List[Tuple[str, str]] = [
        (
            r"\bITEM\s+1A[\.\:\s]+R\s*I\s*S\s*K\s+F\s*A\s*C\s*T\s*O\s*R\s*S\b|\bITEM\s+1A[\.\:\s]+RISK\s+FACTORS\b",
            "Item 1A. Risk Factors",
        ),
        (
            r"\bITEM\s+1B[\.\:\s]+UNRESOLVED\s+STAFF\s+COMMENTS\b",
            "Item 1B. Unresolved Staff Comments",
        ),
        (
            r"\bITEM\s+1C[\.\:\s]+CYBERSECURITY\b",
            "Item 1C. Cybersecurity",
        ),
        (
            r"\bITEM\s+1[\.\:\s]+BUSINESS\b",
            "Item 1. Business",
        ),
        (
            r"\bITEM\s+2[\.\:\s]+PROPERTIES\b",
            "Item 2. Properties",
        ),
        (
            r"\bITEM\s+3[\.\:\s]+LEGAL\s+PROCEEDINGS\b",
            "Item 3. Legal Proceedings",
        ),
        (
            r"\bITEM\s+4[\.\:\s]+MINE\s+SAFETY\s+DISCLOSURES\b",
            "Item 4. Mine Safety Disclosures",
        ),
        (
            r"\bITEM\s+5[\.\:\s]+MARKET\s+FOR\s+REGISTRANT\'?S\s+COMMON\s+EQUITY\b",
            "Item 5. Market for Common Equity",
        ),
        (
            r"\bITEM\s+7A[\.\:\s]+QUANTITATIVE\s+AND\s+QUALITATIVE\s+DISCLOSURES\b",
            "Item 7A. Market Risk Disclosures",
        ),
        (
            r"\bITEM\s+7[\.\:\s]+MANAGEMENT\'?S\s+DISCUSSION\s+AND\s+ANALYSIS\b|\bMD&A\b",
            "Item 7. Management Discussion & Analysis (MD&A)",
        ),
        (
            r"\bITEM\s+8[\.\:\s]+FINANCIAL\s+STATEMENTS\s+AND\s+SUPPLEMENTARY\s+DATA\b",
            "Item 8. Financial Statements & Supplementary Data",
        ),
        (
            r"\bITEM\s+9A[\.\:\s]+CONTROLS\s+AND\s+PROCEDURES\b",
            "Item 9A. Controls & Procedures",
        ),
        (
            r"\bCONSOLIDATED\s+STATEMENTS?\s+OF\s+(?:OPERATIONS|INCOME|EARNINGS)\b",
            "Consolidated Statements of Operations",
        ),
        (
            r"\bCONSOLIDATED\s+BALANCE\s+SHEETS?\b",
            "Consolidated Balance Sheets",
        ),
        (
            r"\bCONSOLIDATED\s+STATEMENTS?\s+OF\s+CASH\s+FLOWS?\b",
            "Consolidated Statements of Cash Flows",
        ),
        (
            r"\bCONSOLIDATED\s+STATEMENTS?\s+OF\s+SHAREHOLDERS\'?\s+EQUITY\b",
            "Consolidated Statements of Equity",
        ),
        (
            r"\bNOTES\s+TO\s+(?:CONSOLIDATED\s+)?FINANCIAL\s+STATEMENTS\b",
            "Notes to Financial Statements",
        ),
        (
            r"\bEXECUTIVE\s+SUMMARY\b|\bEXECUTIVE\s+OVERVIEW\b",
            "Executive Summary",
        ),
    ]

    def __init__(self, initial_section: Optional[str] = None):
        self.current_section = initial_section or self.DEFAULT_SECTION

    def detect_in_text(self, text: str) -> Optional[str]:
        """Scans text for section heading patterns and returns matching section name if found."""
        if not text:
            return None

        for pattern, section_name in self.SECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return section_name
        return None

    def update_and_get_section(self, text: str) -> str:
        """Updates internal active section if a new section heading is found in text."""
        detected = self.detect_in_text(text)
        if detected:
            self.current_section = detected
        return self.current_section


def detect_section_in_text(text: str, default_section: str = "General Information") -> str:
    """Convenience function for standalone section detection on a single text string."""
    detector = SectionDetector(initial_section=default_section)
    return detector.update_and_get_section(text)
