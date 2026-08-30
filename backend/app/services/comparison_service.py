"""
FinSight AI - Multi-Filing Peer & YoY Financial Comparison Service.
Enables side-by-side comparison, variance calculation, and grounded comparative AI narrative.
"""
from typing import Dict, Any, Optional, List
import logging
from ..services.document_service import DocumentService
from ..services.financial_service import FinancialService
from ..llm.llm_client import GeminiLLMClient
from ..rag.rag_service import RAGService
from .cache_service import get_ai_cache_service

logger = logging.getLogger("app.services.comparison_service")


class ComparisonService:
    def __init__(
        self,
        doc_service: Optional[DocumentService] = None,
        fin_service: Optional[FinancialService] = None,
        llm_client: Optional[GeminiLLMClient] = None,
    ):
        self.doc_service = doc_service or DocumentService()
        self.fin_service = fin_service or FinancialService()
        self.llm_client = llm_client or GeminiLLMClient()
        self.rag_service = RAGService()
        self.cache_service = get_ai_cache_service()

    def compare_documents(
        self,
        doc_a_id: str,
        doc_b_id: str,
        user_id: str = "dev_user_123",
        focus_metric: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Extracts financial metrics from both documents, computes delta variances,
        and generates comparative institutional analysis with persistent result caching.
        """
        cache_key = self.cache_service.build_cache_key(
            "comparison",
            user_id=user_id,
            document_id=doc_a_id,
            document_b_id=doc_b_id,
            extra_params={"focus_metric": focus_metric} if focus_metric else None,
        )
        lock = self.cache_service.get_lock_for_key(cache_key)

        with lock:
            cached = self.cache_service.get_cached_result(cache_key, force_refresh=force_refresh)
            if cached:
                return cached

            self.cache_service.set_pending_status(cache_key, "comparison", user_id, [doc_a_id, doc_b_id])

            try:
                res = self._do_compare_documents(doc_a_id, doc_b_id, user_id, focus_metric)
                if res and res.get("comparative_summary"):
                    self.cache_service.save_result(cache_key, "comparison", user_id, [doc_a_id, doc_b_id], res)
                return res
            except Exception as ex:
                self.cache_service.mark_failed(cache_key, str(ex))
                raise ex

    def _do_compare_documents(
        self,
        doc_a_id: str,
        doc_b_id: str,
        user_id: str = "dev_user_123",
        focus_metric: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extracts financial metrics from both documents, computes delta variances,
        and generates comparative institutional analysis.
        """
        logger.info(f"Comparing document '{doc_a_id}' vs '{doc_b_id}' for user '{user_id}'...")

        doc_a = self.doc_service.get_document(doc_a_id, user_id=user_id)
        doc_b = self.doc_service.get_document(doc_b_id, user_id=user_id)

        meta_a = {
            "id": doc_a_id,
            "company_name": getattr(doc_a, "companyName", "Document A") if doc_a else "Document A",
            "financial_year": getattr(doc_a, "financialYear", "Period A") if doc_a else "Period A",
            "file_name": getattr(doc_a, "fileName", f"{doc_a_id}.pdf") if doc_a else f"{doc_a_id}.pdf",
            "page_count": getattr(doc_a, "pageCount", 0) if doc_a else 0,
        }
        meta_b = {
            "id": doc_b_id,
            "company_name": getattr(doc_b, "companyName", "Document B") if doc_b else "Document B",
            "financial_year": getattr(doc_b, "financialYear", "Period B") if doc_b else "Period B",
            "file_name": getattr(doc_b, "fileName", f"{doc_b_id}.pdf") if doc_b else f"{doc_b_id}.pdf",
            "page_count": getattr(doc_b, "pageCount", 0) if doc_b else 0,
        }

        # 1. Fetch Structured Analytics for both filings
        res_a = self.fin_service.extract_chart_data(doc_a_id, user_id=user_id)
        res_b = self.fin_service.extract_chart_data(doc_b_id, user_id=user_id)

        analytics_a = res_a.dict() if hasattr(res_a, "dict") else (res_a.model_dump() if hasattr(res_a, "model_dump") else (res_a or {}))
        analytics_b = res_b.dict() if hasattr(res_b, "dict") else (res_b.model_dump() if hasattr(res_b, "model_dump") else (res_b or {}))

        # 2. Extract Key Financial Ratios / Items
        def get_metric_val(analytics_dict: Dict[str, Any], chart_name: str) -> float:
            items = analytics_dict.get(chart_name, [])
            if items and len(items) > 0:
                last_item = items[-1]
                return float(last_item.get("value", 0.0))
            return 0.0

        rev_a = get_metric_val(analytics_a, "revenue_chart")
        rev_b = get_metric_val(analytics_b, "revenue_chart")

        prof_a = get_metric_val(analytics_a, "profit_chart")
        prof_b = get_metric_val(analytics_b, "profit_chart")

        exp_a = get_metric_val(analytics_a, "expense_chart")
        exp_b = get_metric_val(analytics_b, "expense_chart")

        # 3. Calculate Variances
        def compute_delta(val_a: float, val_b: float) -> Dict[str, Any]:
            abs_diff = round(val_b - val_a, 2)
            pct_change = round(((val_b - val_a) / val_a * 100.0), 2) if val_a != 0 else 0.0
            return {
                "val_a": val_a,
                "val_b": val_b,
                "absolute_delta": abs_diff,
                "percentage_delta": pct_change,
                "trend": "up" if abs_diff > 0 else ("down" if abs_diff < 0 else "neutral"),
            }

        comparison_metrics = [
            {
                "metric_name": "Revenue from Operations",
                "unit": analytics_a.get("currency", "USD/INR"),
                **compute_delta(rev_a, rev_b),
            },
            {
                "metric_name": "Net Profit (PAT)",
                "unit": analytics_a.get("currency", "USD/INR"),
                **compute_delta(prof_a, prof_b),
            },
            {
                "metric_name": "Total Operating Expenses",
                "unit": analytics_a.get("currency", "USD/INR"),
                **compute_delta(exp_a, exp_b),
            },
            {
                "metric_name": "Net Profit Margin",
                "unit": "%",
                **compute_delta(
                    round((prof_a / rev_a * 100.0), 2) if rev_a > 0 else 0.0,
                    round((prof_b / rev_b * 100.0), 2) if rev_b > 0 else 0.0,
                ),
            },
        ]

        # 4. Generate Comparative AI Narrative via LLM
        prompt = f"""You are a Senior Financial Analyst comparing two corporate filings:
Document A: {meta_a['company_name']} ({meta_a['financial_year']})
Document B: {meta_b['company_name']} ({meta_b['financial_year']})

Financial Comparison Data:
- Revenue: {meta_a['company_name']} = {rev_a} | {meta_b['company_name']} = {rev_b}
- Net Profit: {meta_a['company_name']} = {prof_a} | {meta_b['company_name']} = {prof_b}
- Total Expenses: {meta_a['company_name']} = {exp_a} | {meta_b['company_name']} = {exp_b}

Please provide a concise, structured comparative financial summary:
### 1. Key Performance Variance
Summarize the revenue and profitability trajectory between the two filings.

### 2. Operational & Margin Analysis
Highlight operating efficiency, cost trends, and margin shifts.

### 3. Financial Health & Balance Sheet Takeaways
Summarize leverage, solvency, and liquidity differences.

### 4. Strategic Limitations
State what information remains unavailable from the filings alone."""

        ai_narrative = self.llm_client.generate_response(
            prompt=prompt,
            system_instruction="You are an objective financial comparison engine. Output structured markdown.",
            temperature=0.15,
            max_tokens=1500,
        )

        return {
            "document_a": meta_a,
            "document_b": meta_b,
            "metrics": comparison_metrics,
            "analytics_a": analytics_a,
            "analytics_b": analytics_b,
            "comparative_summary": ai_narrative,
        }


def get_comparison_service() -> ComparisonService:
    return ComparisonService()
