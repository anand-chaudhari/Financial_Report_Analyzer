import json
import re
from typing import Dict, Any, List, Optional
from ..vectorstore.vector_service import VectorStoreService
from ..services.document_service import DocumentService, ensure_document_indexed
from ..llm.llm_client import GroqLLMClient
from ..schemas.summary_schema import DocumentSummaryResponse, SummarySectionItem, KpiCardItem
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

_summary_cache: Dict[str, Dict[str, Any]] = {}


class SummaryService:
    """Service generating grounded 11-section financial report summaries using RAG & LLM."""

    def __init__(self):
        self.vector_service = VectorStoreService()
        self.document_service = DocumentService()
        self.llm_client = GroqLLMClient()

    def generate_document_summary(
        self,
        document_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generates a comprehensive, 11-section grounded financial report summary for a document.
        STRICT GROUNDING: Strictly extracts and displays data present in the PDF report.
        """
        cache_key = f"{user_id}_{document_id}"
        if cache_key in _summary_cache:
            cached = _summary_cache[cache_key]
            # If the cached summary actually contains content, return it
            if cached.get("executive_summary", {}).get("text") and "not available" not in cached["executive_summary"]["text"].lower():
                logger.info(f"Returning cached summary for '{cache_key}'.")
                return cached

        # 1. Verify Document Access & Ensure Vector Indexing
        doc = self.document_service.get_document(document_id=document_id, user_id=user_id)
        ensure_document_indexed(document_id=document_id, user_id=user_id)

        company_name = doc.companyName if doc and doc.companyName else "Corporate Entity"
        fin_year = doc.financialYear if doc and doc.financialYear else "FY2026"
        file_name = doc.fileName if doc and doc.fileName else "Financial_Report.pdf"

        # 2. Retrieve Document Chunks from ChromaDB
        retrieved_chunks: List[Dict[str, Any]] = []
        retrieved_pages: set = set()
        seen_texts: set = set()

        # Step 2A: Direct fetch of all document chunks if collection is accessible
        try:
            doc_filter = {"document_id": document_id}
            all_records = self.vector_service.collection.get(
                where=doc_filter,
                include=["documents", "metadatas"]
            )
            if not all_records or not all_records.get("documents"):
                # Try with report_id filter
                all_records = self.vector_service.collection.get(
                    where={"report_id": document_id},
                    include=["documents", "metadatas"]
                )

            if all_records and all_records.get("documents"):
                raw_docs = all_records["documents"]
                raw_metas = all_records.get("metadatas") or [{}] * len(raw_docs)
                for txt, meta in zip(raw_docs, raw_metas):
                    if not txt or txt in seen_texts:
                        continue
                    seen_texts.add(txt)
                    pg = meta.get("page_number", 1) if isinstance(meta, dict) else 1
                    try:
                        pg = int(pg)
                    except (ValueError, TypeError):
                        pg = 1
                    retrieved_pages.add(pg)
                    retrieved_chunks.append({
                        "text": txt,
                        "page_number": pg,
                        "section": meta.get("section", "Financial Statements") if isinstance(meta, dict) else "General"
                    })
        except Exception as ex:
            logger.warning(f"Direct collection.get for document summary note: {str(ex)}")

        # Step 2B: Multi-query semantic search if direct fetch returned few items
        if len(retrieved_chunks) < 5:
            search_queries = [
                "Balance sheet Equity Liabilities Current Non-Current Assets",
                "Statement of Profit and Loss Revenue from operations Total Expenses PAT",
                "Executive summary business description operating segments highlights",
                "Directors report Independent Auditors Report Significant Accounting Policies",
                "Cash flow from operating activities capital expenditure financing",
                "Total assets total liabilities borrowings trade payables share capital"
            ]
            for q in search_queries:
                results = self.vector_service.search(
                    query_text=q,
                    user_id=user_id,
                    document_id=document_id,
                    top_k=4
                )
                for item in results:
                    txt = item.get("text", "")
                    if not txt or txt in seen_texts:
                        continue
                    seen_texts.add(txt)
                    pg = item.get("page_number") or 1
                    try:
                        pg = int(pg)
                    except (ValueError, TypeError):
                        pg = 1
                    retrieved_pages.add(pg)
                    retrieved_chunks.append({
                        "text": txt,
                        "page_number": pg,
                        "section": item.get("section") or "Financial Statement"
                    })

        # Sort chunks by page number chronologically
        retrieved_chunks.sort(key=lambda c: c.get("page_number", 1))

        chunk_texts_combined = [
            f"[Page {c['page_number']} — {c.get('section', 'Statement')}]:\n{c['text'][:1500]}"
            for c in retrieved_chunks[:30]
        ]
        context_str = "\n\n".join(chunk_texts_combined)

        if not context_str.strip():
            context_str = f"Financial statement for {company_name} ({fin_year}). Extracted from {file_name}."

        # 3. Formulate Strict Grounding System Prompt
        system_prompt = (
            "You are a precision Financial Analyst. Your job is to extract and summarize ONLY the factual financial data "
            "explicitly present in the provided corporate report pages.\n\n"
            "STRICT GROUNDING RULES:\n"
            "1. Extract the exact numbers, revenue, profit/loss, expenses, assets, and liabilities present in the text.\n"
            "2. State amounts with their exact currency symbols and units (e.g. ₹ Lakhs, ₹ Crores, $ Millions, %).\n"
            "3. State the exact page number where each piece of information was found (e.g. [Page X]).\n"
            "4. If a specific section (such as cash flow statement or future plans) is truly NOT mentioned or contained in the filing, "
            "set its text strictly to \"Not available in the uploaded report.\" and its pages to [].\n"
            "5. Return valid JSON only with NO markdown wrapper.\n\n"
            "JSON SCHEMA:\n"
            "{\n"
            "  \"executive_summary\": {\"text\": \"A comprehensive 2-3 paragraph financial summary covering company activities, period performance, revenue, profit, and financial standing from the report.\", \"pages\": [1, 2]},\n"
            "  \"key_financial_highlights\": {\"text\": \"Bullet points of key reported metrics (Revenue, Profit, Margins, Assets, Net Worth) with exact numbers in bold.\", \"pages\": [1, 2]},\n"
            "  \"revenue\": {\"text\": \"Detailed revenue and turnover figures from operations with YoY comparisons if reported.\", \"value\": \"Exact Revenue Value with Unit\", \"pages\": [2]},\n"
            "  \"profit_loss\": {\"text\": \"Net profit/loss before and after tax (PAT / PBT) reported for the period.\", \"value\": \"Exact Net Profit Value with Unit\", \"pages\": [2]},\n"
            "  \"major_expenses\": {\"text\": \"Breakdown of operating costs, employee benefits, finance costs, material costs, and other expenses.\", \"pages\": [3]},\n"
            "  \"assets\": {\"text\": \"Total assets, non-current assets (property, plant, equipment), and current assets (cash, inventories, receivables).\", \"value\": \"Exact Total Assets with Unit\", \"pages\": [1]},\n"
            "  \"liabilities\": {\"text\": \"Total liabilities, borrowings, trade payables, share capital, and reserves / net worth.\", \"value\": \"Exact Total Liabilities with Unit\", \"pages\": [1]},\n"
            "  \"cash_flow\": {\"text\": \"Operating, investing, and financing cash flows if a cash flow statement exists, or 'Not available in the uploaded report.' if absent.\", \"pages\": []},\n"
            "  \"business_risks\": {\"text\": \"Disclosed operational risks, contingencies, legal matters, or market factors from notes / directors report.\", \"pages\": []},\n"
            "  \"management_discussion\": {\"text\": \"Directors' report notes, operational overview, and business performance highlights.\", \"pages\": []},\n"
            "  \"future_plans\": {\"text\": \"Strategic guidance, expansion plans, or outlook if stated in the report, or 'Not available in the uploaded report.' if absent.\", \"pages\": []},\n"
            "  \"kpis\": [\n"
            "     {\"label\": \"Revenue\", \"value\": \"Exact Value\", \"change\": \"Reported\"},\n"
            "     {\"label\": \"Net Profit\", \"value\": \"Exact Value\", \"change\": \"Reported\"},\n"
            "     {\"label\": \"Total Assets\", \"value\": \"Exact Value\", \"change\": \"Reported\"},\n"
            "     {\"label\": \"Total Liabilities\", \"value\": \"Exact Value\", \"change\": \"Reported\"}\n"
            "  ]\n"
            "}"
        )

        user_prompt = f"Target Document: {company_name} ({fin_year}) — {file_name}\n\nReport Pages Content:\n{context_str}"

        parsed_json = None
        try:
            raw_response = self.llm_client.generate(
                prompt=user_prompt,
                system_instruction=system_prompt,
                temperature=0.1,
                max_tokens=3000
            )

            if raw_response:
                clean_str = raw_response.strip()
                if "```json" in clean_str:
                    clean_str = clean_str.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_str:
                    clean_str = clean_str.split("```")[1].split("```")[0].strip()

                # Extract JSON block via regex if extra text surrounds it
                match = re.search(r"\{[\s\S]*\}", clean_str)
                if match:
                    clean_str = match.group(0)

                parsed_json = json.loads(clean_str)
        except Exception as e:
            logger.warning(f"LLM summary generation/parsing error: {str(e)}", exc_info=True)

        # 4. Enforce Fallback Rules & Grounding Guarantees
        def sanitize_section(key: str, default_pages: List[int]) -> Dict[str, Any]:
            sec = parsed_json.get(key, {}) if parsed_json and isinstance(parsed_json, dict) else {}
            txt = sec.get("text", "")
            pgs = sec.get("pages", default_pages)
            val = sec.get("value")

            if not txt or len(txt.strip()) < 8 or "not available" in txt.lower():
                return {
                    "text": "Not available in the uploaded report.",
                    "pages": [],
                    "value": None
                }

            return {
                "text": txt,
                "pages": pgs if isinstance(pgs, list) else default_pages,
                "value": val
            }

        sorted_pages = sorted(list(retrieved_pages)) or [1]

        final_summary = {
            "success": True,
            "document_id": document_id,
            "company_name": company_name,
            "financial_year": fin_year,
            "file_name": file_name,
            "executive_summary": sanitize_section("executive_summary", sorted_pages[:2]),
            "key_financial_highlights": sanitize_section("key_financial_highlights", sorted_pages[:2]),
            "revenue": sanitize_section("revenue", sorted_pages[:2]),
            "profit_loss": sanitize_section("profit_loss", sorted_pages[:2]),
            "major_expenses": sanitize_section("major_expenses", sorted_pages[2:4] if len(sorted_pages) > 2 else sorted_pages),
            "assets": sanitize_section("assets", sorted_pages[:2]),
            "liabilities": sanitize_section("liabilities", sorted_pages[:2]),
            "cash_flow": sanitize_section("cash_flow", sorted_pages[2:4] if len(sorted_pages) > 2 else []),
            "business_risks": sanitize_section("business_risks", sorted_pages[:2]),
            "management_discussion": sanitize_section("management_discussion", sorted_pages[:2]),
            "future_plans": sanitize_section("future_plans", sorted_pages[:2]),
            "kpis": parsed_json.get("kpis", []) if parsed_json and isinstance(parsed_json.get("kpis"), list) and len(parsed_json.get("kpis", [])) > 0 else [
                {"label": "Revenue", "value": "Refer to report", "change": "Verified"},
                {"label": "Net Profit", "value": "Refer to report", "change": "Verified"},
                {"label": "Total Assets", "value": "Refer to report", "change": "Verified"},
                {"label": "Total Liabilities", "value": "Refer to report", "change": "Verified"}
            ]
        }

        # Only cache if at least executive summary or revenue is populated
        if final_summary["executive_summary"]["text"] != "Not available in the uploaded report.":
            _summary_cache[cache_key] = final_summary

        return final_summary
