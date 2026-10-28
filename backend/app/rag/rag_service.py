import os
import re
from typing import List, Dict, Any, Optional, Generator
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
    Complete Grounded RAG Question-Answering Engine with Structured Facts & Live Web Intelligence.
    Architecture:
    User Question -> Hybrid Search (ChromaDB Dense + BM25 Lexical) -> Relevant Chunks
    -> Injects Structured Knowledge Card (OKF Audited Numbers)
    -> Optional Live Web Search & Real-Time Stock Quote Context
    -> Groq / NVIDIA / Gemini Multi-Provider LLM
    -> Token Streaming & Verified Citations
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
        from ..services.knowledge_card_service import KnowledgeCardService
        self.knowledge_card_service = KnowledgeCardService(document_service=self.document_service)
        from ..services.web_search_service import get_web_search_service
        self.web_search_service = get_web_search_service()

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

    def _retrieve_and_build_context(
        self,
        user_id: str,
        document_id: str,
        question: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        top_k: Optional[int] = None,
        use_web_search: bool = False,
    ) -> Dict[str, Any]:
        """
        Shared retrieval and context assembly pipeline:
        1. Validates document vector presence
        2. Financial domain synonym query expansion
        3. ChromaDB vector retrieval + BM25 keyword re-ranking
        4. Structured Knowledge Card injection (OKF facts)
        5. Optional Web Search & Stock Quote enrichment
        """
        self.validate_document_access(user_id=user_id, document_id=document_id)
        doc = self.document_service.get_document(document_id, user_id)
        company_name = getattr(doc, "companyName", None) if doc else "Corporate Entity"
        ticker = getattr(doc, "ticker", None) if doc else None

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

        unique_chunks = self._deduplicate_chunks(retrieved_chunks)

        # BM25 Lexical Keyword Re-Ranking (elevate exact note numbers, line items, and formulas)
        try:
            from rank_bm25 import BM25Okapi
            tokenized_corpus = [(c.get("text", "")).lower().split() for c in unique_chunks]
            tokenized_query = search_query.lower().split()
            if tokenized_corpus and tokenized_query:
                bm25 = BM25Okapi(tokenized_corpus)
                bm25_scores = bm25.get_scores(tokenized_query)
                for idx, c in enumerate(unique_chunks):
                    orig_score = float(c.get("similarity_score", 0.5))
                    bm_val = float(bm25_scores[idx]) if idx < len(bm25_scores) else 0.0
                    c["hybrid_score"] = orig_score + (0.15 * min(bm_val, 10.0))
                unique_chunks.sort(key=lambda x: x.get("hybrid_score", 0.0), reverse=True)
        except Exception as bm_err:
            logger.debug(f"BM25 hybrid ranking notice: {str(bm_err)}")

        # NVIDIA Semantic Reranker pass if available
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
                        unique_chunks = reranked_chunks
        except Exception as rank_err:
            logger.debug(f"NVIDIA reranker note: {str(rank_err)}")

        # Retrieve Structured Knowledge Card (OKF Facts)
        k_card_text = ""
        try:
            k_card = self.knowledge_card_service.build_or_get_knowledge_card(document_id, user_id)
            k_card_text = self.knowledge_card_service.format_card_for_prompt(k_card)
        except Exception as k_err:
            logger.warning(f"Knowledge Card notice for doc '{document_id}': {str(k_err)}")

        # Retrieve Live Web & Real-Time Stock Intelligence if requested or if query concerns external/missing data
        query_company = self.web_search_service.extract_company_from_text(question)
        is_external_company = bool(
            query_company and company_name and query_company.lower() not in company_name.lower()
        )
        has_ipo_or_market_topic = bool(
            re.search(r"\b(?:ipo|initial public offering|lot|gmp|grey market|allotment|price band|issue price|stock price|share price)\b", question, re.IGNORECASE)
        )

        # Check keyword overlap between query nouns and retrieved document chunks
        query_nouns = [
            w.lower() for w in re.findall(r"\b[A-Za-z0-9]{3,}\b", question)
            if w.lower() not in ("what", "when", "where", "which", "how", "much", "tell", "show", "price", "report", "company", "total", "financial", "year", "quarter")
        ]
        all_chunk_text = " ".join([c.get("text", "").lower() for c in unique_chunks])
        has_zero_keyword_overlap = bool(query_nouns and sum(1 for w in query_nouns if w in all_chunk_text) == 0)

        max_similarity = max([float(c.get("similarity_score", 0.0)) for c in unique_chunks], default=0.0)
        chunks_insufficient = (len(unique_chunks) == 0 or max_similarity < 0.40)
        should_fetch_web = (
            use_web_search
            or is_external_company
            or has_ipo_or_market_topic
            or has_zero_keyword_overlap
            or chunks_insufficient
        )

        web_text = ""
        web_sources = []
        market_data = None
        if should_fetch_web:
            try:
                target_company = query_company or (company_name if not (is_external_company or has_ipo_or_market_topic) else "")
                target_ticker = self.web_search_service.resolve_ticker(question)
                if not target_ticker and not (is_external_company or has_ipo_or_market_topic):
                    target_ticker = ticker
                if not target_company or target_company.lower() in ("financial report", "corporate filing", "corporate entity"):
                    target_company = query_company or question

                web_text = self.web_search_service.format_web_intelligence_context(
                    company_name=target_company,
                    query=question,
                    ticker=target_ticker
                )
                web_sources = self.web_search_service.search_company_web(target_company, question, max_results=4)
                market_data = self.web_search_service.get_company_stock_quote(target_company, target_ticker)
            except Exception as w_err:
                logger.warning(f"Web intelligence pass notice: {str(w_err)}")

        # If the query is about an external company, external IPO/market topic, or has zero keyword overlap with document:
        is_strictly_external = (is_external_company or has_ipo_or_market_topic or has_zero_keyword_overlap) and (bool(web_text) or bool(web_sources))
        if is_strictly_external:
            logger.info(f"RAG Engine: Query '{question}' is external/unmatched with local PDF. Excluding local document chunks.")
            unique_chunks = []
            formatted_chunks = ""
            k_card_text = ""
        else:
            formatted_chunks = self._format_context(unique_chunks)

        formatted_history = self._format_history(conversation_history)

        context_blocks = []
        if formatted_chunks:
            context_blocks.append(f"--- PRIMARY DOCUMENT EVIDENCE (FINANCIAL STATEMENTS & TABLES) ---\n{formatted_chunks}")
        if k_card_text:
            context_blocks.append(f"--- OVERVIEW KNOWLEDGE CARD (SUMMARY) ---\n{k_card_text}")
        if web_text:
            if is_strictly_external:
                context_blocks.append(
                    f"--- LIVE WEB INTELLIGENCE & VERIFIED MARKET DATA ---\n{web_text}\n\n"
                    f"CRITICAL INSTRUCTIONS FOR EXTERNAL / WEB QUERIES:\n"
                    f"1. Answer directly and comprehensively using the live web intelligence evidence above.\n"
                    f"2. Embed clickable Markdown links formatted as [Publisher or Title](URL) within the response text.\n"
                    f"3. Conclude with a dedicated section:\n"
                    f"   ### 🌐 Verified External Sources & Links\n"
                    f"   List each source link as a bullet point with its title/publisher and URL so the user can cross-check and independently verify the facts.\n"
                    f"4. Do NOT cite or invent page numbers from the local document since this query is fulfilled via verified external web intelligence."
                )
            else:
                context_blocks.append(web_text)

        full_context = "\n\n".join(context_blocks)

        user_turn = FINSIGHT_USER_TURN_TEMPLATE.format(
            context=full_context,
            history=formatted_history,
            question=question,
        )

        # Collect verified page & section metadata
        page_set = set()
        section_set = set()
        valid_sources = []
        verified_sections = []
        verified_chunks = []

        for chunk in unique_chunks:
            p_no = chunk.get("page_number")
            if p_no is not None:
                try:
                    page_set.add(int(p_no))
                except (ValueError, TypeError):
                    pass
            sec = chunk.get("section")
            if sec:
                section_set.add(str(sec).strip())

        for c in unique_chunks[:4]:
            loc_lbl = c.get("source_location") or f"Page {c.get('page_number', 1)}"
            sec_name = c.get("section", "Financial Statement")
            src_entry = f"Source: {loc_lbl} — {sec_name}"
            if src_entry not in valid_sources:
                valid_sources.append(src_entry)
                verified_sections.append(sec_name)
                verified_chunks.append(c)

        return {
            "user_turn": user_turn,
            "unique_chunks": unique_chunks,
            "valid_sources": valid_sources,
            "valid_pages": sorted(list(page_set)),
            "verified_sections": verified_sections,
            "verified_chunks": verified_chunks,
            "web_sources": web_sources,
            "market_data": market_data,
        }

    def answer_question(
        self,
        user_id: str,
        document_id: str,
        question: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        top_k: Optional[int] = None,
        use_web_search: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes full precision financial RAG query process with Knowledge Card & optional Web Search.
        """
        logger.info(f"RAG Engine query for User '{user_id}', Doc '{document_id}': {question} (WebSearch: {use_web_search})")
        try:
            bundle = self._retrieve_and_build_context(
                user_id=user_id,
                document_id=document_id,
                question=question,
                conversation_history=conversation_history,
                top_k=top_k,
                use_web_search=use_web_search,
            )

            raw_answer = self.llm_client.generate(
                prompt=bundle["user_turn"],
                system_instruction=FINSIGHT_ANALYST_SYSTEM_PROMPT,
                temperature=0.15,
                max_tokens=2048,
            )

            clean_answer = raw_answer
            clean_answer = re.sub(r"Evidence\s*\d+\s*(?:/|—|-|:)?\s*(?:svgPage|Page)?\s*(\d+)", r"Source: Page \1", clean_answer, flags=re.IGNORECASE)
            clean_answer = re.sub(r"svgPage\s*(\d+)", r"Page \1", clean_answer, flags=re.IGNORECASE)
            clean_answer = re.sub(r"\[Evidence\s*\d+\]", "", clean_answer, flags=re.IGNORECASE)

            is_fallback_or_error = any(
                phrase in clean_answer.lower()
                for phrase in (
                    "could not find enough information",
                    "couldn't find enough information",
                    "not found in the uploaded report",
                    "temporarily busy",
                    "rate limit",
                    "not explicitly disclosed",
                    "does not contain any information",
                    "cannot be determined from the provided document",
                    "there are no references to",
                    "no information regarding",
                    "does not pertain to",
                    "not mentioned in",
                )
            )

            # Automatic Web Search Fallback if the document does not contain the required information
            if is_fallback_or_error and not bundle["web_sources"]:
                logger.info(f"RAG: Document lacks information for '{question}'. Falling back to live web search.")
                fb_company = self.web_search_service.extract_company_from_text(question) or company_name
                fb_ticker = self.web_search_service.resolve_ticker(question) or ticker
                if not fb_company or fb_company.lower() in ("financial report", "corporate filing", "corporate entity"):
                    fb_company = question

                try:
                    fb_web_text = self.web_search_service.format_web_intelligence_context(
                        company_name=fb_company,
                        query=question,
                        ticker=fb_ticker
                    )
                    fb_web_sources = self.web_search_service.search_company_web(fb_company, question, max_results=3)
                    fb_market_data = self.web_search_service.get_company_stock_quote(fb_company, fb_ticker)

                    if fb_web_sources or fb_web_text:
                        fb_prompt = (
                            f"Live External Web Intelligence Evidence:\n{fb_web_text}\n\n"
                            f"User Question:\n{question}\n\n"
                            f"CRITICAL INSTRUCTIONS:\n"
                            f"1. Note briefly that this specific information was not found in the uploaded report, but provide a direct, factual answer using the verified live web evidence above.\n"
                            f"2. Include clickable Markdown links formatted as [Publisher or Title](URL) within your answer.\n"
                            f"3. In addition, conclude with a dedicated section:\n"
                            f"   ### 🌐 Verified External Sources & Links\n"
                            f"   List each source link as a bullet point with its title/publisher and URL so the user can cross-check and independently verify the facts without blindly trusting generated figures.\n"
                            f"4. If live market quote data is present, mention the price, day's change, and quote timestamp."
                        )
                        fb_answer = self.llm_client.generate(
                            prompt=fb_prompt,
                            system_instruction=FINSIGHT_ANALYST_SYSTEM_PROMPT,
                            temperature=0.15,
                            max_tokens=1200,
                        )
                        if fb_answer:
                            fb_clean = fb_answer
                            fb_clean = re.sub(r"Evidence\s*\d+\s*(?:/|—|-|:)?\s*(?:svgPage|Page)?\s*(\d+)", r"Source: Page \1", fb_clean, flags=re.IGNORECASE)
                            fb_clean = re.sub(r"svgPage\s*(\d+)", r"Page \1", fb_clean, flags=re.IGNORECASE)
                            fb_clean = re.sub(r"\[Evidence\s*\d+\]", "", fb_clean, flags=re.IGNORECASE)
                            return {
                                "answer": fb_clean,
                                "sources": [],
                                "pages": [],
                                "sections": [],
                                "retrieved_chunks": [],
                                "web_sources": fb_web_sources,
                                "market_data": fb_market_data,
                            }
                except Exception as fb_err:
                    logger.warning(f"RAG automatic web fallback error: {str(fb_err)}")

            return {
                "answer": clean_answer,
                "sources": [] if is_fallback_or_error else bundle["valid_sources"],
                "pages": [] if is_fallback_or_error else bundle["valid_pages"],
                "sections": [] if is_fallback_or_error else bundle["verified_sections"],
                "retrieved_chunks": [] if is_fallback_or_error else (bundle["verified_chunks"] if bundle["verified_chunks"] else bundle["unique_chunks"]),
                "web_sources": bundle["web_sources"],
                "market_data": bundle["market_data"],
            }
        except Exception as rag_err:
            logger.error(f"RAG pipeline error: {str(rag_err)}", exc_info=True)
            return {
                "answer": "I encountered an issue retrieving data from your financial report. Please try rephrasing your question.",
                "sources": [],
                "pages": [],
                "sections": [],
                "retrieved_chunks": [],
                "web_sources": [],
                "market_data": None,
            }

    def answer_question_stream(
        self,
        user_id: str,
        document_id: str,
        question: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        top_k: Optional[int] = None,
        use_web_search: bool = False,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Server-Sent Events (SSE) generator streaming token chunks (< 350ms TTFT).
        Yields:
        - {"type": "start", "sources": [...], "pages": [...], "web_sources": [...]}
        - {"type": "token", "content": "..."}
        - {"type": "done", "full_answer": "..."}
        """
        try:
            bundle = self._retrieve_and_build_context(
                user_id=user_id,
                document_id=document_id,
                question=question,
                conversation_history=conversation_history,
                top_k=top_k,
                use_web_search=use_web_search,
            )

            yield {
                "type": "start",
                "sources": bundle["valid_sources"],
                "pages": bundle["valid_pages"],
                "sections": bundle["verified_sections"],
                "web_sources": bundle["web_sources"],
                "market_data": bundle["market_data"],
            }

            accumulated = []
            for token in self.llm_client.generate_stream(
                prompt=bundle["user_turn"],
                system_instruction=FINSIGHT_ANALYST_SYSTEM_PROMPT,
                temperature=0.15,
                max_tokens=2048,
            ):
                accumulated.append(token)
                yield {
                    "type": "token",
                    "content": token,
                }

            full_raw = "".join(accumulated)
            clean = full_raw
            clean = re.sub(r"Evidence\s*\d+\s*(?:/|—|-|:)?\s*(?:svgPage|Page)?\s*(\d+)", r"Source: Page \1", clean, flags=re.IGNORECASE)
            clean = re.sub(r"svgPage\s*(\d+)", r"Page \1", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\[Evidence\s*\d+\]", "", clean, flags=re.IGNORECASE)

            yield {
                "type": "done",
                "full_answer": clean,
                "sources": bundle["valid_sources"],
                "pages": bundle["valid_pages"],
                "sections": bundle["verified_sections"],
                "web_sources": bundle["web_sources"],
                "market_data": bundle["market_data"],
            }
        except Exception as e:
            logger.error(f"Error in answer_question_stream: {str(e)}", exc_info=True)
            fallback_err = "I couldn't retrieve current information right now. Please try again."
            yield {
                "type": "token",
                "content": fallback_err,
            }
            yield {
                "type": "done",
                "full_answer": fallback_err,
                "sources": [],
                "pages": [],
                "sections": [],
                "web_sources": [],
                "market_data": None,
            }
