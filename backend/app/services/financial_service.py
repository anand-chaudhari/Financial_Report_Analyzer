import json
from typing import Dict, Any, Optional, List
from ..vectorstore.vector_service import VectorStoreService
from ..llm.llm_client import GroqLLMClient
from ..rag.prompts import FINANCIAL_SUMMARY_PROMPT, FINANCIAL_ANALYTICS_EXTRACTION_PROMPT
from ..schemas.financial_schema import (
    FinancialSummaryResponse,
    FinancialChartDataResponse,
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
