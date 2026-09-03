import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rag.rag_service import RAGService
from app.rag.financial_calculator import FinancialCalculator, parse_financial_number
from app.rag.prompts import FINSIGHT_ANALYST_SYSTEM_PROMPT


def test_financial_calculator_yoy_growth():
    """Verify deterministic Python calculation for YoY revenue growth."""
    res = FinancialCalculator.calculate_yoy_growth(
        current_val=240893,
        previous_val=225458,
        metric_name="Revenue from Operations",
        unit="Cr",
        currency="₹",
    )
    assert res["success"] is True
    assert res["growth_percent"] == 6.85
    assert res["absolute_change"] == 15435.0
    assert "+6.85%" in res["formatted_result"]
    assert "Formula: YoY Growth" in res["formula_string"]


def test_financial_calculator_margin():
    """Verify deterministic Python calculation for EBITDA and Net Profit margins."""
    res_ebitda = FinancialCalculator.calculate_margin(
        metric_val=73713,
        revenue_val=240893,
        margin_name="EBITDA Margin",
        unit="Cr",
        currency="₹",
    )
    assert res_ebitda["success"] is True
    assert res_ebitda["margin_percent"] == 30.6
    assert "30.60%" in res_ebitda["formatted_result"]

    res_pat = FinancialCalculator.calculate_margin(
        metric_val=48313,
        revenue_val=240893,
        margin_name="PAT Margin",
        unit="Cr",
        currency="₹",
    )
    assert res_pat["success"] is True
    assert res_pat["margin_percent"] == 20.06


def test_financial_calculator_ratios():
    """Verify deterministic Python calculations for financial ratios."""
    res_de = FinancialCalculator.calculate_ratio(
        numerator_val=28500,
        denominator_val=145800,
        ratio_name="Debt-to-Equity Ratio",
    )
    assert res_de["success"] is True
    assert res_de["ratio_value"] == 0.20
    assert res_de["formatted_result"] == "0.20x"

    res_cr = FinancialCalculator.calculate_ratio(
        numerator_val=92200,
        denominator_val=45000,
        ratio_name="Current Ratio",
    )
    assert res_cr["success"] is True
    assert res_cr["ratio_value"] == 2.05


def test_rag_system_prompt_accuracy_rules():
    """Verify FINSIGHT_ANALYST_SYSTEM_PROMPT includes strict financial accuracy instructions."""
    assert "STRICT FINANCIAL ACCURACY & GROUNDING RULES" in FINSIGHT_ANALYST_SYSTEM_PROMPT
    assert "PREFER EXACT TABLE VALUES OVER NARRATIVE SUMMARIES" in FINSIGHT_ANALYST_SYSTEM_PROMPT
    assert "PRESERVE UNITS, CURRENCY, AND FINANCIAL YEAR" in FINSIGHT_ANALYST_SYSTEM_PROMPT
    assert "DETERMINISTIC CALCULATIONS & STEP-BY-STEP FORMULAS" in FINSIGHT_ANALYST_SYSTEM_PROMPT
    assert "EVERY NUMERICAL ANSWER MUST CITE ITS SOURCE LOCATION" in FINSIGHT_ANALYST_SYSTEM_PROMPT


from app.vectorstore.vector_service import VectorStoreService
from app.llm.llm_client import GroqLLMClient


def test_rag_service_financial_query_expansion_and_evidence():
    """Verify RAGService retrieves relevant financial tables and passes structured context with sources."""
    mock_vector = MagicMock(spec=VectorStoreService)
    mock_vector.document_exists.return_value = True

    table_chunk = {
        "chunk_id": "chunk_p42_1",
        "page_number": 42,
        "section": "Statement of Profit and Loss",
        "source_location": "Page 42",
        "similarity_score": 0.95,
        "text": "| Particulars | FY2026 (₹ Cr) | FY2025 (₹ Cr) |\n| --- | --- | --- |\n| Revenue from Operations | 240,893 | 225,458 |\n| Profit After Tax (PAT) | 48,313 | 43,908 |",
    }

    mock_vector.search.return_value = [table_chunk]

    mock_doc_service = MagicMock()
    mock_doc_service.ensure_document_indexed.return_value = True

    mock_llm = MagicMock(spec=GroqLLMClient)
    mock_llm.generate.return_value = (
        "### 1. Direct Answer\n"
        "Revenue from Operations was **₹240,893 Crore** in **FY2026**, representing a **+6.85%** YoY growth. (Source: Statement of Profit and Loss, Page 42)\n\n"
        "### 2. Key Report Findings\n"
        "- **Revenue from Operations**: **₹240,893 Crore** in **FY2026** vs **₹225,458 Crore** in **FY2025**.\n"
        "- **Profit After Tax (PAT)**: **₹48,313 Crore** in **FY2026** vs **₹43,908 Crore** in **FY2025**.\n\n"
        "### 3. Financial Indicators & Calculations\n"
        "- **YoY Growth**: `((240,893 - 225,458) / 225,458) * 100 = +6.85%`\n\n"
        "### 4. Limitations & Missing Information\n"
        "Segment-wise revenue split is not present on this page.\n\n"
        "### 5. Sources\n"
        "- Page 42 — Statement of Profit and Loss"
    )

    mock_nv = MagicMock()
    mock_nv.is_available = False

    rag = RAGService(
        vector_service=mock_vector,
        document_service=mock_doc_service,
        llm_client=mock_llm,
        nvidia_client=mock_nv,
    )

    res = rag.answer_question(
        user_id="user_fin",
        document_id="doc_fin",
        question="What was the revenue and PAT in FY2026?"
    )

    assert "₹240,893 Crore" in res["answer"]
    assert "₹48,313 Crore" in res["answer"]
    assert 42 in res["pages"]
    assert len(res["sources"]) > 0
    assert "Page 42" in res["sources"][0]
    print("[PASS] Test Financial RAG Query Expansion and Evidence Passed.")


if __name__ == "__main__":
    test_financial_calculator_yoy_growth()
    test_financial_calculator_margin()
    test_financial_calculator_ratios()
    test_rag_system_prompt_accuracy_rules()
    test_rag_service_financial_query_expansion_and_evidence()
    print("\nALL FINANCIAL RAG ACCURACY TESTS PASSED!")
