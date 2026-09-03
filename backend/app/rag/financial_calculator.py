"""
FinSight AI - Deterministic Financial Calculator
Provides pure Python, deterministic financial computations:
- YoY Growth Rate (%)
- Financial Margins (EBITDA Margin, Net Profit Margin, Operating Margin %)
- Financial Ratios (Debt-to-Equity, Current Ratio, Quick Ratio, ROE)
- Formats step-by-step formula explanations for RAG grounding
"""
import re
from typing import Optional, Dict, Any, Union


def parse_financial_number(val_str: Union[str, int, float]) -> Optional[float]:
    """Cleans currency symbols, commas, and parentheses for negative numbers."""
    if isinstance(val_str, (int, float)):
        return float(val_str)
    if not val_str or not isinstance(val_str, str):
        return None

    s = val_str.strip().replace(",", "").replace("₹", "").replace("$", "").replace("€", "").replace("£", "").replace("%", "").strip()

    # Handle (1,200) as -1200
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1].strip()

    try:
        return float(s)
    except ValueError:
        # Check for regex number match
        m = re.search(r"[-+]?\d*\.?\d+", s)
        if m:
            try:
                return float(m.group(0))
            except ValueError:
                return None
        return None


class FinancialCalculator:
    """Deterministic financial calculations with formatted formulas."""

    @staticmethod
    def calculate_yoy_growth(
        current_val: Union[str, float],
        previous_val: Union[str, float],
        metric_name: str = "Metric",
        unit: str = "Cr",
        currency: str = "₹",
    ) -> Dict[str, Any]:
        """
        Formula: Growth (%) = ((Current - Previous) / |Previous|) * 100
        """
        c = parse_financial_number(current_val)
        p = parse_financial_number(previous_val)

        if c is None or p is None or p == 0:
            return {
                "success": False,
                "error": "Invalid or zero denominator for YoY calculation.",
                "explanation": "Cannot compute growth rate: previous period value is missing or zero."
            }

        growth_pct = ((c - p) / abs(p)) * 100.0
        abs_change = c - p
        sign = "+" if growth_pct >= 0 else ""

        formula_str = (
            f"Formula: YoY Growth = ((Current Year - Previous Year) / Previous Year) × 100\n"
            f"Inputs: Current = {currency}{c:,.2f} {unit}, Previous = {currency}{p:,.2f} {unit}\n"
            f"Calculation: (({currency}{c:,.2f} - {currency}{p:,.2f}) / {currency}{abs(p):,.2f}) × 100 = {sign}{growth_pct:.2f}%\n"
            f"Absolute Change: {sign}{currency}{abs_change:,.2f} {unit}"
        )

        return {
            "success": True,
            "metric_name": metric_name,
            "current_value": c,
            "previous_value": p,
            "growth_percent": round(growth_pct, 2),
            "absolute_change": round(abs_change, 2),
            "formula_string": formula_str,
            "formatted_result": f"{sign}{growth_pct:.2f}%",
        }

    @staticmethod
    def calculate_margin(
        metric_val: Union[str, float],
        revenue_val: Union[str, float],
        margin_name: str = "Margin",
        unit: str = "Cr",
        currency: str = "₹",
    ) -> Dict[str, Any]:
        """
        Formula: Margin (%) = (Metric / Revenue) * 100
        """
        m = parse_financial_number(metric_val)
        r = parse_financial_number(revenue_val)

        if m is None or r is None or r == 0:
            return {
                "success": False,
                "error": "Invalid or zero revenue for margin calculation.",
                "explanation": "Cannot compute margin: revenue value is missing or zero."
            }

        margin_pct = (m / r) * 100.0

        formula_str = (
            f"Formula: {margin_name} = ({margin_name.split()[0]} / Revenue) × 100\n"
            f"Inputs: {margin_name.split()[0]} = {currency}{m:,.2f} {unit}, Revenue = {currency}{r:,.2f} {unit}\n"
            f"Calculation: ({currency}{m:,.2f} / {currency}{r:,.2f}) × 100 = {margin_pct:.2f}%"
        )

        return {
            "success": True,
            "margin_name": margin_name,
            "margin_percent": round(margin_pct, 2),
            "formula_string": formula_str,
            "formatted_result": f"{margin_pct:.2f}%",
        }

    @staticmethod
    def calculate_ratio(
        numerator_val: Union[str, float],
        denominator_val: Union[str, float],
        ratio_name: str = "Ratio",
        unit: str = "",
    ) -> Dict[str, Any]:
        """
        Formula: Ratio = Numerator / Denominator
        """
        num = parse_financial_number(numerator_val)
        den = parse_financial_number(denominator_val)

        if num is None or den is None or den == 0:
            return {
                "success": False,
                "error": "Invalid or zero denominator for ratio calculation.",
                "explanation": "Cannot compute ratio: denominator value is missing or zero."
            }

        ratio_val = num / den

        formula_str = (
            f"Formula: {ratio_name} = Numerator / Denominator\n"
            f"Inputs: Numerator = {num:,.2f}, Denominator = {den:,.2f}\n"
            f"Calculation: {num:,.2f} / {den:,.2f} = {ratio_val:.2f}x"
        )

        return {
            "success": True,
            "ratio_name": ratio_name,
            "ratio_value": round(ratio_val, 2),
            "formula_string": formula_str,
            "formatted_result": f"{ratio_val:.2f}x",
        }
