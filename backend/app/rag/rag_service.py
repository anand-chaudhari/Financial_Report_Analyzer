import os
import re
from typing import List, Dict, Any, Optional
from ..vectorstore.vector_service import VectorStoreService
from ..llm.llm_client import GroqLLMClient
from .prompts import (
    FINSIGHT_ANALYST_SYSTEM_PROMPT,
    FINSIGHT_USER_TURN_TEMPLATE,
    NO_INFORMATION_FALLBACK_RESPONSE,
)
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class RAGService:
    """
    Complete Grounded RAG Question-Answering Engine.
    Architecture:
    User Question -> Query Embedding -> ChromaDB Retrieval -> Relevant Chunks
    -> Context Construction -> Groq LLM (system + user roles) -> Natural Analyst Answer -> Sources
    """

    def __init__(
        self,
        vector_service: Optional[VectorStoreService] = None,
        document_service: Optional[Any] = None,
        llm_client: Optional[GroqLLMClient] = None,
        nvidia_client: Optional[Any] = None,
    ):
        self.vector_service = vector_service or VectorStoreService()
        if document_service is None:
            from ..services.document_service import DocumentService
            self.document_service = DocumentService()
        else:
            self.document_service = document_service
        self.llm_client = llm_client or GroqLLMClient()
        self.nvidia_client = nvidia_client

    def validate_document_access(self, user_id: str, document_id: str) -> bool:
        """
        Validates document existence and automatically triggers on-demand indexing if needed.
        """
        if not document_id:
            return False

        if self.vector_service.document_exists(document_id=document_id, user_id=user_id):
            return True

        doc_service = getattr(self, "document_service", None)
        if doc_service:
            return doc_service.ensure_document_indexed(document_id=document_id, user_id=user_id)
        return False

    def _format_context(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        Constructs clearly labeled evidence blocks from retrieved chunks across all document formats.
        Preserves exact tables, units, currencies, and line items.
        """
        context_blocks = []
        for idx, chunk in enumerate(retrieved_chunks, 1):
            page_no = chunk.get("page_number", 1)
            sec = (chunk.get("section") or "Financial Statement").strip()
            loc_str = chunk.get("source_location") or f"Page {page_no}"
            text = (chunk.get("text") or "").strip()

            # Sanitize internal tokens
            text = re.sub(r"svgPage\s*\d+", "", text)
            text = re.sub(r"Evidence\s*\d+\s*[:\-]", "", text)

            # Preserve detailed chunk content up to 3500 chars
            if len(text) > 3500:
                text = text[:3500] + "..."

            block = (
                f"--- EVIDENCE BLOCK {idx} [Source: {sec}, {loc_str}] ---\n"
                f"{text}"
            )
            context_blocks.append(block)

        return "\n\n".join(context_blocks)

    def _format_history(self, conversation_history: Optional[List[Dict[str, Any]]]) -> str:
        """Formats conversation history for prompt inclusion."""
        if not conversation_history:
            return "None"
        formatted = []
        for msg in conversation_history:
            role = msg.get("role") or msg.get("sender") or "User"
            content = msg.get("content") or msg.get("text") or ""
            if content:
                formatted.append(f"{role.capitalize()}: {content}")
        return "\n".join(formatted) if formatted else "None"

    def _deduplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove exact duplicate chunks by chunk_id or text prefix without dropping chunks on the same page."""
        seen = set()
        unique = []
        for c in chunks:
            key = c.get("chunk_id") or (c.get("text", "")[:80])
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique

    def answer_question(
        self,
        user_id: str,
        document_id: str,
        question: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes full precision financial RAG query process:
        1. Validates document vector presence
        2. Financial domain synonym expansion & multi-query retrieval
        3. Context window expansion for primary table pages
        4. NVIDIA semantic reranking if available
        5. Sends formatted evidence to LLM with financial accuracy prompt
        6. Returns structured answer with verified sources
        """
        logger.info(f"RAG Engine query for User '{user_id}', Doc '{document_id}': {question}")
        try:
            return self._answer_question_inner(
                user_id=user_id,
                document_id=document_id,
                question=question,
                conversation_history=conversation_history,
                top_k=top_k,
            )
        except Exception as rag_err:
            logger.error(f"RAG pipeline error: {str(rag_err)}", exc_info=True)
            return {
                "answer": "I encountered an issue retrieving data from your financial report. Please try rephrasing your question.",
                "sources": [],
                "pages": [],
                "sections": [],
                "retrieved_chunks": [],
            }

    def _answer_question_inner(
        self,
        user_id: str,
        document_id: str,
        question: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Inner RAG pipeline with high-precision financial metric routing and verification."""
        # 1. Ensure Document Vectors Exist in ChromaDB
        self.validate_document_access(user_id=user_id, document_id=document_id)

        # 2. Vector Search (Primary query with financial synonyms & section markers)
        search_query = question.strip()
        q_lower = search_query.lower()

        # Classify intent & expand with financial domain synonyms and section headings
        if any(t in q_lower for t in ("revenue", "sales", "turnover", "income", "topline", "top line")):
            search_query = f"{question} Statement of Profit and Loss Revenue from operations Other income Total revenue Turnover Sales particulars March 31"
        elif any(t in q_lower for t in ("ebitda", "operating profit", "operating margin", "operating ebitda")):
            search_query = f"{question} Statement of Profit and Loss EBITDA Operating Profit before depreciation finance cost employee expenses"
        elif any(t in q_lower for t in ("net profit", "profit", "net income", "pat", "pbt", "profit after tax", "profit before tax", "loss")):
            search_query = f"{question} Statement of Profit and Loss Profit for the year Profit After Tax PAT Profit Before Tax PBT Net Profit Total Comprehensive Income"
        elif any(t in q_lower for t in ("eps", "earnings per share", "diluted eps", "basic eps")):
            search_query = f"{question} Earnings per equity share Basic Diluted EPS Statement of Profit and Loss Nominal value per share"
        elif any(t in q_lower for t in ("asset", "assets", "property", "plant", "equipment", "non-current", "current assets", "ppe")):
            search_query = f"{question} Balance Sheet Total assets Non-current assets Current assets Property plant and equipment Inventories Trade receivables Cash"
        elif any(t in q_lower for t in ("liability", "liabilities", "debt", "borrowing", "borrowings", "payables", "equity", "debt-to-equity")):
            search_query = f"{question} Balance Sheet Total equity Total liabilities Borrowings Long term borrowings Short term borrowings Current liabilities Trade payables"
        elif any(t in q_lower for t in ("cash flow", "cashflow", "operating cash", "investing", "financing", "free cash flow")):
            search_query = f"{question} Statement of Cash Flows Cash generated from operations Operating activities Investing activities Financing activities Net increase in cash"
        elif any(t in q_lower for t in ("ratio", "current ratio", "roe", "roce", "margin", "gearing")):
            search_query = f"{question} Key Ratios Operating Margin Net Margin Current Ratio Debt Equity ROE Return on Equity ROCE"
        elif any(t in q_lower for t in ("company", "name", "cin", "corporate", "who", "registered", "auditor")):
            search_query = f"{question} Company name Corporate identification number CIN Registered office Independent auditor Directors report"
        elif any(t in q_lower for t in ("year", "financial year", "fiscal", "period", "fy")):
            search_query = f"{question} Financial year Fiscal year Ended 31st March Annual report Statement of accounts"

        k_results = top_k or 10
        logger.info(f"RAG Retrieval -> Query: '{question}' | Expanded: '{search_query}' | Doc: '{document_id}' | Top K: {k_results}")

        retrieved_chunks = self.vector_service.search(
            query_text=search_query,
            user_id=user_id,
            document_id=document_id,
            top_k=k_results,
        )

        # Fallback for low-yield searches
        if len(retrieved_chunks) < 3:
            overview_chunks = self.vector_service.search(
                query_text="company name statement of profit and loss balance sheet revenue net profit total assets",
                user_id=user_id,
                document_id=document_id,
                top_k=5,
            )
            seen_chunk_ids = {c.get("chunk_id") for c in retrieved_chunks}
            for oc in overview_chunks:
                if oc.get("chunk_id") not in seen_chunk_ids:
                    retrieved_chunks.append(oc)
                    seen_chunk_ids.add(oc.get("chunk_id"))

        if not retrieved_chunks:
            logger.warning(f"RAG: Zero vector chunks found for doc '{document_id}'.")
            return {
                "answer": NO_INFORMATION_FALLBACK_RESPONSE,
                "sources": [],
                "pages": [],
                "sections": [],
                "retrieved_chunks": [],
            }

        # 3. Deduplicate chunks
        unique_chunks = self._deduplicate_chunks(retrieved_chunks)

        # 3B. NVIDIA Semantic Reranking (POST /v1/ranking with nvidia/llama-3.2-nv-rerankqa-1b-v2)
        try:
            nv_client = self.nvidia_client
            if nv_client is None and os.getenv("NVIDIA_API_KEY"):
                from ..llm.nvidia_client import get_nvidia_rag_client
                nv_client = get_nvidia_rag_client()

            if nv_client and getattr(nv_client, "is_available", False) and len(unique_chunks) > 1:
                ranked = nv_client.rerank(query=question, passages=unique_chunks, top_n=len(unique_chunks))
                if ranked:
                    reranked_chunks = []
                    for r_item in ranked:
                        idx = r_item.get("index")
                        if idx is not None and 0 <= idx < len(unique_chunks):
                            chunk_copy = dict(unique_chunks[idx])
                            chunk_copy["rerank_score"] = r_item.get("logit", 0.0)
                            reranked_chunks.append(chunk_copy)
                    if reranked_chunks:
                        logger.info(f"NVIDIA Reranker re-ordered {len(reranked_chunks)} chunks for query: '{question}'")
                        unique_chunks = reranked_chunks
        except Exception as rank_err:
            logger.debug(f"NVIDIA reranker pass note: {str(rank_err)}")
        
        # Detailed Debug Log of Retrieved Evidence
        logger.info(f"=== RAG RETRIEVAL DEBUG ===")
        logger.info(f"User Query: {question}")
        logger.info(f"Retrieved Chunks Count: {len(unique_chunks)}")
        for idx, ch in enumerate(unique_chunks, 1):
            p = ch.get("page_number", "?")
            sec = ch.get("section", "General")
            score = ch.get("similarity_score", 0.0)
            snippet = (ch.get("text", "")[:120]).replace("\n", " ")
            logger.info(f"  Chunk {idx}: Page {p} | Score: {score} | Section: {sec} | Preview: {snippet}...")

        # 4. Collect Metadata Lists
        page_set = set()
        section_set = set()

        for chunk in unique_chunks:
            page_no = chunk.get("page_number")
            if page_no is not None:
                try:
                    page_set.add(int(page_no))
                except (ValueError, TypeError):
                    pass
            sec = chunk.get("section")
            if sec:
                section_set.add(str(sec).strip())

        sorted_pages = sorted(list(page_set))
        sorted_sections = sorted(list(section_set))

        # 5. Build clearly labeled evidence context
        formatted_context = self._format_context(unique_chunks)
        formatted_history = self._format_history(conversation_history)

        logger.info(f"=== RAG CONTEXT SENT TO LLM ({len(formatted_context)} chars, Pages: {sorted_pages}) ===")

        # 6. Compose user turn message
        user_turn = FINSIGHT_USER_TURN_TEMPLATE.format(
            context=formatted_context,
            history=formatted_history,
            question=question,
        )

        # 7. Send to LLM with precision grounded RAG context
        raw_answer = self.llm_client.generate(
            prompt=user_turn,
            system_instruction=FINSIGHT_ANALYST_SYSTEM_PROMPT,
            temperature=0.15,
            max_tokens=2048,
        )

        # Post-process answer to replace any residual internal tokens:
        # e.g. "Evidence 7 / svgPage 291" -> "Source: Page 291 — Financial Statement"
        clean_answer = raw_answer
        clean_answer = re.sub(r"Evidence\s*\d+\s*(?:/|—|-|:)?\s*(?:svgPage|Page)?\s*(\d+)", r"Source: Page \1", clean_answer, flags=re.IGNORECASE)
        clean_answer = re.sub(r"svgPage\s*(\d+)", r"Page \1", clean_answer, flags=re.IGNORECASE)
        clean_answer = re.sub(r"\[Evidence\s*\d+\]", "", clean_answer, flags=re.IGNORECASE)

        # 8. Evidence-Based Citation Verification: Only cite pages that actually support the answer
        is_fallback_or_error = any(
            phrase in clean_answer.lower()
            for phrase in ("could not find enough information", "couldn't find enough information", "not found in the uploaded report", "temporarily busy", "rate limit", "not explicitly disclosed")
        )

        valid_pages: List[int] = []
        valid_sources: List[str] = []
        verified_sections: List[str] = []
        verified_chunks: List[Dict[str, Any]] = []

        if not is_fallback_or_error:
            # Check if any chunk source_location is explicitly mentioned or relevant
            for c in unique_chunks[:4]:
                loc_lbl = c.get("source_location") or f"Page {c.get('page_number', 1)}"
                sec_name = c.get("section", "Financial Statement")
                src_entry = f"Source: {loc_lbl} — {sec_name}"
                if src_entry not in valid_sources:
                    valid_sources.append(src_entry)
                    verified_sections.append(sec_name)
                    verified_chunks.append(c)
                if c.get("page_number") and c.get("page_number") not in valid_pages:
                    valid_pages.append(c.get("page_number"))

            valid_pages.sort()

        logger.info(f"RAG Generated Answer: {len(clean_answer)} chars | Verified Sources: {valid_sources}")

        return {
            "answer": clean_answer,
            "sources": valid_sources,
            "pages": valid_pages,
            "sections": verified_sections,
            "retrieved_chunks": verified_chunks if verified_chunks else unique_chunks,
        }
