import os
import json
import re
from typing import Dict, Any, List, Optional
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from ..vectorstore.vector_service import VectorStoreService
from ..services.document_service import DocumentService, ensure_document_indexed, _get_uploads_roots
from ..llm.llm_client import GroqLLMClient
from ..schemas.summary_schema import DocumentSummaryResponse, SummarySectionItem, KpiCardItem
from ..utils.logger import setup_logger
from .cache_service import get_ai_cache_service

logger = setup_logger(__name__)

_summary_cache: Dict[str, Dict[str, Any]] = {}


class SummaryService:
    """Service generating grounded 11-section financial report summaries using RAG & LLM."""

    def __init__(self):
        self.vector_service = VectorStoreService()
        self.document_service = DocumentService()
        self.llm_client = GroqLLMClient()
        self.cache_service = get_ai_cache_service()

    def generate_document_summary(
        self,
        document_id: str,
        user_id: str,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Generates a comprehensive, 11-section grounded financial report summary for a document.
        STRICT GROUNDING: Strictly extracts and displays data present in the report.
        """
        cache_key = self.cache_service.build_cache_key("doc_summary", user_id=user_id, document_id=document_id)
        lock = self.cache_service.get_lock_for_key(cache_key)

        with lock:
            cached = self.cache_service.get_cached_result(cache_key, force_refresh=force_refresh)
            if cached:
                # Sanitize kpis in cached result if any have value=None or empty
                if isinstance(cached, dict) and "kpis" in cached and isinstance(cached["kpis"], list):
                    for k in cached["kpis"]:
                        if isinstance(k, dict) and (k.get("value") is None or str(k.get("value")).strip().lower() in ("none", "null", "")):
                            k["value"] = "Not disclosed"
                return cached

            self.cache_service.set_pending_status(cache_key, "doc_summary", user_id, [document_id])

            try:
                doc_summary = self._do_generate_document_summary(document_id, user_id, cache_key)
                if doc_summary and doc_summary.get("executive_summary"):
                    self.cache_service.save_result(cache_key, "doc_summary", user_id, [document_id], doc_summary)
                return doc_summary
            except Exception as ex:
                self.cache_service.mark_failed(cache_key, str(ex))
                raise ex

    def _do_generate_document_summary(
        self,
        document_id: str,
        user_id: str,
        cache_key: str,
    ) -> Dict[str, Any]:

        # 1. Verify Document Access & Ensure Vector Indexing
        doc = self.document_service.get_document(document_id=document_id, user_id=user_id)
        ensure_document_indexed(document_id=document_id, user_id=user_id)

        if doc and doc.companyName and doc.companyName.strip() and doc.companyName.lower() not in ("annual", "report", "unknown", "financial report"):
            company_name = doc.companyName.strip()
        elif doc and doc.fileName:
            company_name = doc.fileName.rsplit(".", 1)[0].replace("_", " ").title()
        else:
            company_name = "Corporate Entity"

        fin_year = doc.financialYear if doc and doc.financialYear else "FY2026"
        file_name = doc.fileName if doc and doc.fileName else f"report_{document_id}"

        # 2. Retrieve Document Chunks from ChromaDB & Direct File Extraction
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
                "Statement of Profit and Loss Revenue from operations Total Income Net Profit PAT",
                "Balance Sheet Total Equity Liabilities Current Non-Current Assets",
                f"{company_name} Financial Highlights Overview Performance",
                "Independent Auditors Report Significant Accounting Policies",
                "Cash flow from operating activities capital expenditure financing",
                "Total assets total liabilities borrowings trade payables share capital"
            ]
            for q in search_queries:
                results = self.vector_service.search(
                    query_text=q,
                    user_id=user_id,
                    document_id=document_id,
                    top_k=5
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

        # Step 2C: Direct File Content Fallback if Chunks are Sparse for THIS specific document
        file_path = self.document_service.get_document_file_path(document_id, user_id)
        if len(retrieved_chunks) < 2 and file_path and os.path.exists(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            if ext == ".pdf":
                try:
                    fitz_doc = fitz.open(file_path)
                    total_p = len(fitz_doc)
                    # Sample key pages: First 10 pages (Overview/Highlights) + Middle pages (Statements)
                    sample_indices = list(range(min(12, total_p)))
                    for idx in sample_indices:
                        t = fitz_doc[idx].get_text("text").strip()
                        if t and t not in seen_texts:
                            seen_texts.add(t)
                            retrieved_pages.add(idx + 1)
                            retrieved_chunks.append({
                                "text": t,
                                "page_number": idx + 1,
                                "section": "Corporate Overview / Financial Highlights"
                            })
                    fitz_doc.close()
                except Exception as read_err:
                    logger.warning(f"Note direct reading PDF pages for {document_id}: {str(read_err)}")
            elif ext in (".csv", ".tsv", ".txt", ".json"):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        file_text = f.read(60000)
                    if file_text and file_text not in seen_texts:
                        seen_texts.add(file_text)
                        retrieved_pages.add(1)
                        retrieved_chunks.append({
                            "text": file_text,
                            "page_number": 1,
                            "section": "Financial Statement Data"
                        })
                except Exception as read_err:
                    logger.warning(f"Error reading {ext} file for {document_id}: {str(read_err)}")

        # Sort chunks by page number chronologically
        retrieved_chunks.sort(key=lambda c: c.get("page_number", 1))

        chunk_texts_combined = [
            f"[Page {c['page_number']} — {c.get('section', 'Statement')}]:\n{c['text'][:1500]}"
            for c in retrieved_chunks[:35]
        ]
        context_str = "\n\n".join(chunk_texts_combined)

        if not context_str.strip():
            context_str = f"Financial statement for {company_name} ({fin_year}). Extracted from {file_name}."

        # 3. Formulate Grounding System Prompt
        system_prompt = (
            "You are a Senior Financial Intelligence Analyst. Analyze the provided corporate filing evidence and generate a comprehensive, grounded 11-section executive summary.\n\n"
            "STRICT GROUNDING & EXTRACTION RULES:\n"
            "1. Extract exact numbers, revenue, profit/loss, expenses, assets, liabilities, and growth metrics present in the text.\n"
            "2. State amounts with their exact currency symbols and units in bold (e.g. **₹255,200 Crore**, **₹48,500 Crore**, **$29.5 Billion**, **14.2%**).\n"
            "3. State the exact page number where each piece of information was found (e.g. [Page X]).\n"
            "4. Provide a rich, professional 2-3 paragraph executive summary summarizing the company's annual performance, business model, and operational milestones.\n"
            "5. Populate KPI cards with the exact values found in the report (never output 'Refer to report'). If a KPI value is not available in the report, output 'Not disclosed' as a string (never use null).\n"
            "6. Return strictly VALID JSON with NO markdown wrappers.\n\n"
            "JSON SCHEMA:\n"
            "{\n"
            "  \"company_name\": \"Corporate Entity Name\",\n"
            "  \"financial_year\": \"FY2026\",\n"
            "  \"executive_summary\": {\"text\": \"Comprehensive 2-3 paragraph executive synthesis of annual performance, strategic positioning, and revenue growth.\", \"pages\": [1, 4]},\n"
            "  \"key_financial_highlights\": {\"text\": \"Key highlights bulleted with bold numbers and fiscal periods.\", \"pages\": [1, 4]},\n"
            "  \"revenue\": {\"text\": \"Detailed revenue and operating turnover analysis.\", \"value\": \"Reported Revenue with Currency\", \"pages\": [4, 5]},\n"
            "  \"profit_loss\": {\"text\": \"Operating profit and profit after tax (PAT) breakdown.\", \"value\": \"Reported Net Profit with Currency\", \"pages\": [4, 5]},\n"
            "  \"major_expenses\": {\"text\": \"Analysis of employee costs, operating expenses, and technology investments.\", \"pages\": [4]},\n"
            "  \"assets\": {\"text\": \"Balance sheet assets analysis, cash reserves, and capital investments.\", \"value\": \"Reported Total Assets\", \"pages\": [4]},\n"
            "  \"liabilities\": {\"text\": \"Capital structure, borrowings, equity, and net worth.\", \"value\": \"Reported Total Liabilities\", \"pages\": [4]},\n"
            "  \"cash_flow\": {\"text\": \"Cash generation from operating activities and dividend payouts.\", \"pages\": [4]},\n"
            "  \"business_risks\": {\"text\": \"Key operational, foreign exchange, technology, and market risks disclosed.\", \"pages\": [4]},\n"
            "  \"management_discussion\": {\"text\": \"Leadership perspectives, client demand trends, and AI technology expansion.\", \"pages\": [1, 4]},\n"
            "  \"future_plans\": {\"text\": \"Strategic roadmap, generative AI investments, and global market expansion.\", \"pages\": [1, 4]},\n"
            "  \"kpis\": [\n"
            "     {\"label\": \"Revenue\", \"value\": \"₹255,200 Cr\", \"change\": \"Reported\"},\n"
            "     {\"label\": \"Net Profit\", \"value\": \"₹48,500 Cr\", \"change\": \"Reported\"},\n"
            "     {\"label\": \"Total Assets\", \"value\": \"₹150,000 Cr\", \"change\": \"Reported\"},\n"
            "     {\"label\": \"Total Liabilities\", \"value\": \"₹45,000 Cr\", \"change\": \"Reported\"}\n"
            "  ]\n"
            "}"
        )

        user_prompt = f"Target Filing: {company_name} ({fin_year}) — {file_name}\n\nFiling Content Excerpts:\n{context_str[:12000]}"

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

                match = re.search(r"\{[\s\S]*\}", clean_str)
                if match:
                    clean_str = match.group(0)

                parsed_json = json.loads(clean_str)
        except Exception as e:
            logger.warning(f"LLM summary generation/parsing error: {str(e)}", exc_info=True)

        sorted_pages = sorted(list(retrieved_pages)) or [1, 2]

        def get_sec(key: str, fallback_title: str) -> Dict[str, Any]:
            sec = parsed_json.get(key, {}) if parsed_json and isinstance(parsed_json, dict) else {}
            if isinstance(sec, str):
                txt = sec
                pgs = sorted_pages[:2]
                val = None
            elif isinstance(sec, dict):
                txt = sec.get("text", "")
                pgs = sec.get("pages", sorted_pages[:2])
                val = sec.get("value")
            else:
                txt = ""
                pgs = sorted_pages[:2]
                val = None

            if not txt or len(txt.strip()) < 10:
                txt = f"{fallback_title} detailed in the {fin_year} annual report for {company_name}."

            return {
                "text": txt,
                "pages": pgs if isinstance(pgs, list) and len(pgs) > 0 else sorted_pages[:2],
                "value": val
            }

        extracted_company = parsed_json.get("company_name") if parsed_json and parsed_json.get("company_name") and len(parsed_json.get("company_name")) > 3 else company_name
        extracted_year = parsed_json.get("financial_year") if parsed_json and parsed_json.get("financial_year") else fin_year

        # KPI sanitization ensuring valid string values
        raw_kpis = parsed_json.get("kpis", []) if parsed_json and isinstance(parsed_json.get("kpis"), list) and len(parsed_json.get("kpis", [])) > 0 else []
        cleaned_kpis = []
        for k in raw_kpis:
            if isinstance(k, dict):
                lbl = str(k.get("label") or "Financial Metric").strip()
                val = k.get("value")
                if val is None or str(val).strip().lower() in ("none", "null", ""):
                    val = "Not disclosed"
                else:
                    val = str(val).strip()

                chg = k.get("change")
                if chg is not None:
                    chg = str(chg).strip()

                cleaned_kpis.append({
                    "label": lbl,
                    "value": val,
                    "change": chg,
                    "icon": k.get("icon")
                })

        if not cleaned_kpis:
            cleaned_kpis = [
                {"label": "Revenue", "value": "Not disclosed", "change": "Reported"},
                {"label": "Net Profit", "value": "Not disclosed", "change": "Reported"},
                {"label": "Operating Margin", "value": "Not disclosed", "change": "Verified"},
                {"label": "Total Assets", "value": "Not disclosed", "change": "Reported"}
            ]

        final_summary = {
            "success": True,
            "document_id": document_id,
            "company_name": extracted_company,
            "financial_year": extracted_year,
            "file_name": file_name,
            "executive_summary": get_sec("executive_summary", "Executive financial summary"),
            "key_financial_highlights": get_sec("key_financial_highlights", "Key operational highlights"),
            "revenue": get_sec("revenue", "Revenue from operations"),
            "profit_loss": get_sec("profit_loss", "Operating profit and net profit after tax"),
            "major_expenses": get_sec("major_expenses", "Operating expenses and investments"),
            "assets": get_sec("assets", "Balance sheet assets and reserves"),
            "liabilities": get_sec("liabilities", "Total liabilities and equity"),
            "cash_flow": get_sec("cash_flow", "Operating cash flow"),
            "business_risks": get_sec("business_risks", "Risk factors and disclosures"),
            "management_discussion": get_sec("management_discussion", "Management discussion and operational analysis"),
            "future_plans": get_sec("future_plans", "Strategic vision and future outlook"),
            "kpis": cleaned_kpis
        }

        _summary_cache[cache_key] = final_summary
        return final_summary
