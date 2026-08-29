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
    ):
        self.vector_service = vector_service or VectorStoreService()
        if document_service is None:
            from ..services.document_service import DocumentService
            self.document_service = DocumentService()
        else:
            self.document_service = document_service
        self.llm_client = llm_client or GroqLLMClient()

    def validate_document_access(self, user_id: str, document_id: str) -> bool:
        """
        Validates document existence and automatically triggers on-demand indexing if needed.
        """
        if not document_id:
            return False

        if self.vector_service.document_exists(document_id=document_id, user_id=user_id):
            return True

        return self.document_service.ensure_document_indexed(document_id=document_id, user_id=user_id)

    def _format_context(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        Constructs clearly labeled evidence blocks from retrieved chunks.
        Preserves full text of the chunks so detailed tables, metrics, and explanations are not truncated.
        """
        context_blocks = []
        for idx, chunk in enumerate(retrieved_chunks, 1):
            page_no = chunk.get("page_number", 1)
            sec = (chunk.get("section") or "Financial Statement").strip()
            text = (chunk.get("text") or "").strip()

            # Sanitize internal OCR tokens
            text = re.sub(r"svgPage\s*\d+", "", text)
            text = re.sub(r"Evidence\s*\d+\s*[:\-]", "", text)

            # Preserve detailed chunk content up to 3000 chars
            if len(text) > 3000:
                text = text[:3000] + "..."

            block = (
                f"[Page {page_no} — {sec}]\n"
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
        Executes full RAG query process:
        1. Validate ownership & trigger on-demand vector indexing if needed
        2. Vector search & filter by document_id and user_id (top_k default=8)
        3. Deduplicate and build labeled evidence context
        4. Send system prompt + user turn to Groq LLM
        5. Return natural-language answer, structured sources, and retrieved_chunks
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
        """Inner RAG pipeline - isolated so errors are caught by answer_question wrapper."""
        # 1. Ensure Document Vectors Exist in ChromaDB
        self.validate_document_access(user_id=user_id, document_id=document_id)

        # 2. Vector Search (Primary query with semantic financial term expansion)
        search_query = question.strip()
        q_lower = search_query.lower()
        
        if any(t in q_lower for t in ("revenue", "sales", "turnover", "income", "topline", "top line")):
            search_query = f"{question} Statement of Profit and Loss Revenue from operations Other income Total revenue Total income turnover"
        elif any(t in q_lower for t in ("net profit", "profit", "net income", "pat", "pbt", "profit after tax", "profit before tax", "loss")):
            search_query = f"{question} Statement of Profit and Loss Profit After Tax PAT Profit Before Tax PBT Net Profit Net Income Total Comprehensive Income"
        elif any(t in q_lower for t in ("asset", "assets", "property", "plant", "equipment", "non-current", "current assets")):
            search_query = f"{question} Balance sheet Total assets Non-current assets Current assets Property plant and equipment Inventories Trade receivables"
        elif any(t in q_lower for t in ("liability", "liabilities", "debt", "borrowing", "borrowings", "payables", "equity")):
            search_query = f"{question} Balance sheet Total equity Total liabilities Borrowings Current liabilities Non-current liabilities Trade payables"
        elif any(t in q_lower for t in ("company", "name", "cin", "corporate", "who", "registered", "auditor")):
            search_query = f"{question} Company name Corporate identification number CIN Registered office Independent auditor Directors report"
        elif any(t in q_lower for t in ("year", "financial year", "fiscal", "period", "fy")):
            search_query = f"{question} Financial year Fiscal year Ended 31st March Annual report Statement of accounts"
        elif any(t in q_lower for t in ("cash flow", "cashflow", "operating cash", "investing", "financing")):
            search_query = f"{question} Statement of cash flows Cash generated from operations Operating activities Investing activities Financing activities"
        elif any(t in q_lower for t in ("invest", "stock", "buy", "hold", "worth", "valuation", "recommendation", "fundamental")):
            search_query = f"{question} Statement of Profit and Loss Net Income Total Revenue Balance Sheet Total Assets Total Debt Cash Flows Operating Margin Key Risks"

        k_results = top_k or 10
        logger.info(f"RAG Retrieval -> Query: '{question}' | Expanded: '{search_query}' | Doc: '{document_id}' | Top K: {k_results}")
        
        retrieved_chunks = self.vector_service.search(
            query_text=search_query,
            user_id=user_id,
            document_id=document_id,
            top_k=k_results,
        )

        # Broad multi-query fallback for high-level summaries or low-yield searches
        if len(retrieved_chunks) < 4:
            overview_chunks = self.vector_service.search(
                query_text="company name statement of profit and loss balance sheet revenue from operations net profit total assets total equity and liabilities",
                user_id=user_id,
                document_id=document_id,
                top_k=8,
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

        # Locate PDF file on disk for full multimodal document vision
        pdf_path = None
        base_uploads = os.path.join(os.getcwd(), "uploads")
        if os.path.exists(base_uploads):
            user_doc_dir = os.path.join(base_uploads, user_id, document_id)
            if os.path.exists(user_doc_dir):
                pdfs = [f for f in os.listdir(user_doc_dir) if f.lower().endswith(".pdf")]
                if pdfs:
                    pdf_path = os.path.join(user_doc_dir, pdfs[0])
            
            if not pdf_path:
                all_pdfs = []
                for root, dirs, files in os.walk(base_uploads):
                    for f in files:
                        if f.lower().endswith(".pdf"):
                            fp = os.path.join(root, f)
                            all_pdfs.append((os.path.getmtime(fp), fp))
                if all_pdfs:
                    all_pdfs.sort(reverse=True)
                    pdf_path = all_pdfs[0][1]

        # 7. Send to LLM
        raw_answer = self.llm_client.generate(
            prompt=user_turn,
            system_instruction=FINSIGHT_ANALYST_SYSTEM_PROMPT,
            temperature=0.15,
            max_tokens=2048,
            pdf_path=pdf_path,
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
            for phrase in ("could not find enough information", "not found in the uploaded report", "temporarily busy", "rate limit", "not explicitly disclosed")
        )

        valid_pages: List[int] = []
        valid_sources: List[str] = []
        verified_sections: List[str] = []
        verified_chunks: List[Dict[str, Any]] = []

        if not is_fallback_or_error:
            # Extract explicitly cited page numbers from the generated response
            cited_pages = set()
            for p_match in re.finditer(r"(?:Page|p\.)\s*(\d+)", clean_answer, re.IGNORECASE):
                try:
                    p_val = int(p_match.group(1))
                    if p_val in page_set:
                        cited_pages.add(p_val)
                except ValueError:
                    pass

            if cited_pages:
                valid_pages = sorted(list(cited_pages))
            else:
                # If LLM cited no explicit pages, use top chunks with highest relevance score
                valid_pages = sorted_pages[:2]

            for p in valid_pages:
                # Find matching chunk to extract exact section name
                matching_chunk = next((c for c in unique_chunks if c.get("page_number") == p), None)
                sec_name = matching_chunk.get("section", "Financial Statement") if matching_chunk else "Financial Statement"
                valid_sources.append(f"Source: Page {p} — {sec_name}")
                verified_sections.append(sec_name)
                if matching_chunk:
                    verified_chunks.append(matching_chunk)

        logger.info(f"RAG Generated Answer: {len(clean_answer)} chars | Verified Cited Pages: {valid_pages}")

        return {
            "answer": clean_answer,
            "sources": valid_sources,
            "pages": valid_pages,
            "sections": verified_sections,
            "retrieved_chunks": verified_chunks if verified_chunks else unique_chunks,
        }
