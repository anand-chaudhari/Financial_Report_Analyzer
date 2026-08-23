import re
from typing import List


class TextCleaner:
    """
    Cleaner for financial PDF documents.
    Normalizes whitespace and removes control characters while strictly preserving:
    - Monetary symbols ($, €, £, ¥, ₹)
    - Percentages (e.g. 46.2%, +12.9%)
    - Financial figures and negative indicators (e.g. $383,285, (1,234.50), -15.4%)
    - Dates and period headers (e.g. September 28, 2024, Q3 FY24)
    - Section headings and line breaks relevant to financial statement tables
    """

    @staticmethod
    def clean(text: str) -> str:
        if not text:
            return ""

        # 1. Replace non-breaking spaces and zero-width spaces
        cleaned = text.replace("\u00a0", " ").replace("\u200b", "").replace("\xad", "")

        # 2. Strip non-printable ASCII control characters (preserving \n and \t)
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)

        # 3. Replace multiple horizontal spaces/tabs on a single line with a single space
        cleaned = re.sub(r"[ \t]+", " ", cleaned)

        # 4. Normalize excessive newlines (3 or more consecutive newlines reduced to 2)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # 5. Trim whitespace per line while preserving nonempty lines
        lines = [line.strip() for line in cleaned.split("\n")]
        cleaned = "\n".join(line for line in lines if line)

        return cleaned.strip()


def clean_financial_text(text: str) -> str:
    """Convenience functional wrapper around TextCleaner.clean."""
    return TextCleaner.clean(text)
