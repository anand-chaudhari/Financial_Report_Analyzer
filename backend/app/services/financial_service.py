import json
import re
from typing import Dict, Any, Optional, List
from ..vectorstore.vector_service import VectorStoreService
from ..llm.llm_client import GroqLLMClient
from ..rag.prompts import FINANCIAL_SUMMARY_PROMPT, FINANCIAL_ANALYTICS_EXTRACTION_PROMPT
from ..schemas.financial_schema import (
    FinancialSummaryResponse,
    FinancialChartDataResponse,
    FinancialOverviewResponse,
    OverviewMetricItem,
    MetricDataPoint,
    AssetsLiabilitiesPoint,
    CashFlowPoint,
    YoYComparisonPoint,
    KeyRatio,
)
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class FinancialService:
    """
    Service handling executive financial summaries and precision chart data extraction.
    Strict Grounding Enforced: Does NOT invent, hallucinate, or generate mock numbers.
    """

    def __init__(
        self,
        vector_service: Optional[VectorStoreService] = None,
        llm_client: Optional[GroqLLMClient] = None,
    ):
        self.vector_service = vector_service or VectorStoreService()
        self.llm_client = llm_client or GroqLLMClient()

    def generate_summary(self, report_id: str, user_id: str) -> FinancialSummaryResponse:
        """Generates structured executive summary and key highlights from report chunks."""
        chunks = self.vector_service.search(
            query_text="Executive summary financial results highlights overview revenue profit business performance",
            user_id=user_id,
            document_id=report_id,
            top_k=6,
        )

        if not chunks:
            return FinancialSummaryResponse(
                report_id=report_id,
                company_name="Corporate Report",
                fiscal_period="N/A",
                currency="USD",
                executive_summary="No sufficient structured text chunks available in the report to generate an executive summary.",
                key_highlights=[],
                risks_and_challenges=[],
            )

        context_text = "\n\n".join(
            f"[Page {c.get('page_number', 1)}] [Section: {c.get('section', 'General')}]: {c.get('text', '')}"
            for c in chunks
        )

        prompt = FINANCIAL_SUMMARY_PROMPT.format(context=context_text)
        raw_response = self.llm_client.generate(prompt=prompt, temperature=0.1, max_tokens=1000)

        try:
            cleaned_json = raw_response.strip()
            if "```json" in cleaned_json:
                cleaned_json = cleaned_json.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_json:
                cleaned_json = cleaned_json.split("```")[1].split("```")[0].strip()

            parsed = json.loads(cleaned_json)
            return FinancialSummaryResponse(
                report_id=report_id,
                company_name=parsed.get("company_name", "Corporate Entity"),
                fiscal_period=parsed.get("fiscal_period", "Fiscal Year"),
                currency=parsed.get("currency", "USD"),
                executive_summary=parsed.get("executive_summary", raw_response),
                key_highlights=parsed.get("key_highlights", []),
                risks_and_challenges=parsed.get("risks_and_challenges", []),
            )
        except Exception as e:
            logger.warning(f"Failed to parse financial summary JSON: {str(e)}")
            return FinancialSummaryResponse(
                report_id=report_id,
                executive_summary=raw_response or "Executive summary could not be extracted.",
                key_highlights=[],
                risks_and_challenges=[],
            )

    def extract_chart_data(self, report_id: str, user_id: str) -> FinancialChartDataResponse:
        """
        Extracts structured time-series metrics formatted for Recharts.
        STRICT GROUNDING: Returns has_data=False and empty charts if no reliable numbers found.
        """
        chunks = self.vector_service.search(
            query_text="Consolidated Financial Statements Statement of Operations Income Revenue Net Profit Operating Expenses Balance Sheet Assets Liabilities Cash Flows",
            user_id=user_id,
            document_id=report_id,
            top_k=10,
        )

        if not chunks:
            logger.info(f"No vector chunks found for report '{report_id}' financial charts.")
            return FinancialChartDataResponse(
                report_id=report_id,
                company_name="Financial Filing",
                has_data=False,
                currency="USD",
            )

        context_text = "\n\n".join(
            f"[Page {c.get('page_number', 1)}] [Section: {c.get('section', 'Financial Statement')}]: {c.get('text', '')[:700]}"
            for c in chunks
        )

        prompt = FINANCIAL_ANALYTICS_EXTRACTION_PROMPT.format(context=context_text)
        raw_response = self.llm_client.generate(prompt=prompt, temperature=0.0, max_tokens=1500)

        try:
            cleaned_json = raw_response.strip()
            if "```json" in cleaned_json:
                cleaned_json = cleaned_json.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_json:
                cleaned_json = cleaned_json.split("```")[1].split("```")[0].strip()

            parsed = json.loads(cleaned_json)

            rev_chart = [MetricDataPoint(**item) for item in parsed.get("revenue_chart", []) if isinstance(item, dict) and item.get("value") is not None]
            profit_chart = [MetricDataPoint(**item) for item in parsed.get("profit_chart", []) if isinstance(item, dict) and item.get("value") is not None]
            expense_chart = [MetricDataPoint(**item) for item in parsed.get("expense_chart", []) if isinstance(item, dict) and item.get("value") is not None]
            assets_liab_chart = [AssetsLiabilitiesPoint(**item) for item in parsed.get("assets_vs_liabilities_chart", []) if isinstance(item, dict)]
            cf_chart = [CashFlowPoint(**item) for item in parsed.get("cash_flow_chart", []) if isinstance(item, dict)]
            yoy_chart = [YoYComparisonPoint(**item) for item in parsed.get("yoy_comparison_chart", []) if isinstance(item, dict)]
            ratios = [KeyRatio(**item) for item in parsed.get("key_ratios", []) if isinstance(item, dict)]

            has_valid_data = bool(
                parsed.get("has_data", False) and (
                    rev_chart or profit_chart or expense_chart or assets_liab_chart or cf_chart or yoy_chart
                )
            )

            return FinancialChartDataResponse(
                report_id=report_id,
                company_name=parsed.get("company_name", "Financial Filing"),
                has_data=has_valid_data,
                currency=parsed.get("currency", "USD"),
                revenue_chart=rev_chart,
                profit_chart=profit_chart,
                expense_chart=expense_chart,
                assets_vs_liabilities_chart=assets_liab_chart,
                cash_flow_chart=cf_chart,
                yoy_comparison_chart=yoy_chart,
                key_ratios=ratios,
                raw_metrics=parsed,
            )

        except Exception as e:
            logger.error(f"Failed to parse financial chart data JSON for report '{report_id}': {str(e)}")
            # Strictly return empty charts without inventing numbers when extraction fails
            return FinancialChartDataResponse(
                report_id=report_id,
                company_name="Financial Filing",
                has_data=False,
                currency="USD",
            )

    get_financial_analytics = extract_chart_data

    def get_financial_overview(self, report_id: str, user_id: str) -> FinancialOverviewResponse:
        """
        Feature 2: Extracts automatic grounded Financial Overview comparing FY2025 vs FY2026.
        Extracts only numbers actually available in the report. Missing values default to 'Not available in the report'.
        """
        # 1. Retrieve Statement Chunks from ChromaDB
        chunks = self.vector_service.search(
            query_text="Balance sheet Profit and Loss Revenue from Operations Net Profit EPS Total Assets Total Liabilities Equity Reserves Cash Flow Statement Key Ratios",
            user_id=user_id,
            document_id=report_id,
            top_k=12,
        )

        if not chunks:
            # Fallback direct fetch of document chunks
            try:
                records = self.vector_service.collection.get(where={"document_id": report_id}, include=["documents", "metadatas"])
                if records and records.get("documents"):
                    for txt, meta in zip(records["documents"][:15], records.get("metadatas", [])[:15]):
                        chunks.append({
                            "text": txt,
                            "page_number": meta.get("page_number", 1) if isinstance(meta, dict) else 1,
                            "section": meta.get("section", "Financial Statement") if isinstance(meta, dict) else "General"
                        })
            except Exception as e:
                logger.debug(f"Direct chunk fetch note in get_financial_overview: {str(e)}")

        default_item = lambda name: OverviewMetricItem(
            name=name,
            fy2025_value="Not available in the report",
            fy2026_value="Not available in the report",
            growth="Not available in the report",
            is_available=False
        )

        if not chunks:
            return FinancialOverviewResponse(
                report_id=report_id,
                company_name="Corporate Filing",
                has_data=False,
                revenue=default_item("Revenue"),
                net_profit=default_item("Net Profit"),
                eps=default_item("EPS"),
                total_assets=default_item("Total Assets"),
                total_liabilities=default_item("Total Liabilities"),
                equity=default_item("Equity / Net Worth"),
                cash_flow=default_item("Cash Flow"),
                important_ratios=[],
                executive_overview="Financial overview could not be generated as no text chunks were indexed."
            )

        context_text = "\n\n".join(
            f"[Page {c.get('page_number', 1)}] [Section: {c.get('section', 'Statement')}]:\n{c.get('text', '')[:1200]}"
            for c in chunks[:15]
        )

        prompt = f"""You are a precision Financial Analyst. Extract the following exact reported metrics comparing FY2025 vs FY2026 (or whichever prior vs current fiscal periods exist in the filing).

STRICT GROUNDING RULES:
1. Extract only values explicitly reported in the text.
2. If a specific metric or fiscal period is NOT mentioned, set its value strictly to "Not available in the report".
3. Do NOT guess or hallucinate numbers or ratios.
4. Return valid JSON only with NO markdown block.

JSON Schema:
{{
  "company_name": "Exact company name or Corporate Entity",
  "currency": "Currency code (e.g. INR, USD)",
  "reporting_periods": ["FY2025", "FY2026"],
  "revenue": {{"name": "Revenue from Operations", "fy2025_value": "...", "fy2026_value": "...", "growth": "...", "unit": "...", "page_number": 2, "is_available": true}},
  "net_profit": {{"name": "Net Profit (PAT)", "fy2025_value": "...", "fy2026_value": "...", "growth": "...", "unit": "...", "page_number": 2, "is_available": true}},
  "eps": {{"name": "Earnings Per Share (EPS)", "fy2025_value": "...", "fy2026_value": "...", "growth": "...", "unit": "...", "page_number": 2, "is_available": true}},
  "total_assets": {{"name": "Total Assets", "fy2025_value": "...", "fy2026_value": "...", "growth": "...", "unit": "...", "page_number": 1, "is_available": true}},
  "total_liabilities": {{"name": "Total Liabilities", "fy2025_value": "...", "fy2026_value": "...", "growth": "...", "unit": "...", "page_number": 1, "is_available": true}},
  "equity": {{"name": "Shareholders Equity / Net Worth", "fy2025_value": "...", "fy2026_value": "...", "growth": "...", "unit": "...", "page_number": 1, "is_available": true}},
  "cash_flow": {{"name": "Operating Cash Flow", "fy2025_value": "...", "fy2026_value": "...", "growth": "...", "unit": "...", "page_number": 3, "is_available": true}},
  "important_ratios": [
     {{"name": "Net Profit Margin", "fy2025_value": "...", "fy2026_value": "...", "growth": "...", "unit": "%", "page_number": 2, "is_available": true}},
     {{"name": "Current Ratio", "fy2025_value": "...", "fy2026_value": "...", "growth": "...", "unit": "x", "page_number": 1, "is_available": true}},
     {{"name": "Debt to Equity", "fy2025_value": "...", "fy2026_value": "...", "growth": "...", "unit": "x", "page_number": 1, "is_available": true}}
  ],
  "executive_overview": "A 2-sentence neutral overview of reported revenue and net profit performance."
}}

Filing Context:
{context_text}"""

        raw_response = self.llm_client.generate(prompt=prompt, temperature=0.0, max_tokens=2000)

        try:
            clean_str = raw_response.strip()
            if "```json" in clean_str:
                clean_str = clean_str.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_str:
                clean_str = clean_str.split("```")[1].split("```")[0].strip()

            match = re.search(r"\{[\s\S]*\}", clean_str)
            if match:
                clean_str = match.group(0)

            parsed = json.loads(clean_str)

            def build_item(key: str, label: str) -> OverviewMetricItem:
                data = parsed.get(key, {})
                if not isinstance(data, dict):
                    return default_item(label)
                v25 = data.get("fy2025_value") or "Not available in the report"
                v26 = data.get("fy2026_value") or "Not available in the report"
                growth = data.get("growth") or "Not available in the report"
                avail = bool((v25 and "not available" not in v25.lower()) or (v26 and "not available" not in v26.lower()))
                return OverviewMetricItem(
                    name=data.get("name", label),
                    fy2025_value=v25,
                    fy2026_value=v26,
                    growth=growth,
                    unit=data.get("unit"),
                    page_number=data.get("page_number"),
                    is_available=avail
                )

            ratios_list = []
            for r in parsed.get("important_ratios", []):
                if isinstance(r, dict):
                    ratios_list.append(OverviewMetricItem(
                        name=r.get("name", "Ratio"),
                        fy2025_value=r.get("fy2025_value") or "Not available in the report",
                        fy2026_value=r.get("fy2026_value") or "Not available in the report",
                        growth=r.get("growth") or "Not available in the report",
                        unit=r.get("unit"),
                        page_number=r.get("page_number"),
                        is_available=True
                    ))

            return FinancialOverviewResponse(
                report_id=report_id,
                company_name=parsed.get("company_name", "Corporate Filing"),
                currency=parsed.get("currency", "USD"),
                has_data=True,
                reporting_periods=parsed.get("reporting_periods", ["FY2025", "FY2026"]),
                revenue=build_item("revenue", "Revenue from Operations"),
                net_profit=build_item("net_profit", "Net Profit (PAT)"),
                eps=build_item("eps", "Earnings Per Share (EPS)"),
                total_assets=build_item("total_assets", "Total Assets"),
                total_liabilities=build_item("total_liabilities", "Total Liabilities"),
                equity=build_item("equity", "Shareholders Equity / Net Worth"),
                cash_flow=build_item("cash_flow", "Operating Cash Flow"),
                important_ratios=ratios_list,
                executive_overview=parsed.get("executive_overview", "")
            )

        except Exception as ex:
            logger.warning(f"Error parsing financial overview JSON: {str(ex)}")
            return FinancialOverviewResponse(
                report_id=report_id,
                company_name="Corporate Filing",
                has_data=False,
                revenue=default_item("Revenue"),
                net_profit=default_item("Net Profit"),
                eps=default_item("EPS"),
                total_assets=default_item("Total Assets"),
                total_liabilities=default_item("Total Liabilities"),
                equity=default_item("Equity / Net Worth"),
                cash_flow=default_item("Cash Flow"),
                important_ratios=[],
                executive_overview="Grounded financial overview generated from corporate filing."
            )

