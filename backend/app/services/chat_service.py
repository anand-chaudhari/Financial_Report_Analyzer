"""
FinSight AI — Chat & Conversational RAG Service.
Implements smart intent classification (Categories A–E), predictable web-search toggle handling (AUTO/ON/OFF),
and natural human-friendly conversational responses without technical implementation leakage.
"""
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Generator
from ..schemas.chat_schema import ChatResponse, Citation
from ..rag.rag_service import RAGService
from ..rag.prompts import (
    FINSIGHT_CONVERSATIONAL_SYSTEM_PROMPT,
    FINSIGHT_ANALYST_SYSTEM_PROMPT,
)
from .conversation_service import ConversationService
from .cache_service import get_ai_cache_service
from .intent_service import get_intent_router, IntentType
from .web_search_service import get_web_search_service
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def clean_user_facing_response(text: str) -> str:
    """
    Cleans response text to ensure zero developer implementation leakage,
    raw symbols, or internal IDs reach the end user.
    """
    if not text:
        return ""
    cleaned = text
    # Remove internal evidence / vector tags
    cleaned = re.sub(r"\[Evidence\s*\d+\]", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"Evidence\s*\d+\s*(?:/|—|-|:)?\s*(?:svgPage|Page)?\s*(\d+)", r"Page \1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"svgPage\s*(\d+)", r"Page \1", cleaned, flags=re.IGNORECASE)

    # Strip internal developer debug expressions
    leakage_patterns = [
        r"(?i)\b(?:RAG retrieval returned \d+ chunks?\.?|BM25 ranked[^\n.;]*[.;]?|ChromaDB found[^\n.;]*[.;]?|SSE stream completed[^\n.;]*[.;]?|Intent=[^\s;\n]+;?)",
        r"(?i)\b(?:doc_[a-f0-9]{8,16}|chunk_[a-z0-9_]+)\b",
    ]
    for lp in leakage_patterns:
        cleaned = re.sub(lp, "", cleaned)

    # Clean double spaces and triple+ newlines
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


class ChatService:
    """
    Service handling multi-turn institutional chat, intent routing, and grounded RAG synthesis.
    Integrates live stock quotes, DuckDuckGo search discovery, and persistent conversation history.
    """

    def __init__(
        self,
        rag_service: Optional[RAGService] = None,
        conv_service: Optional[ConversationService] = None,
    ):
        self.rag_service = rag_service or RAGService()
        self.conv_service = conv_service or ConversationService()
        self.cache_service = get_ai_cache_service()
        self.intent_router = get_intent_router()
        self.web_search_service = get_web_search_service()

    def _resolve_effective_mode(self, search_mode: Optional[str] = None, use_web_search: Optional[bool] = None) -> str:
        """Resolves effective search mode between 'auto', 'on', 'off', and 'web_only'."""
        if search_mode and str(search_mode).strip().lower() in ("auto", "on", "off", "web_only", "@websearch"):
            val = str(search_mode).strip().lower()
            return "web_only" if val in ("web_only", "@websearch") else val
        if use_web_search is True:
            return "on"
        if use_web_search is False:
            return "off"
        return "auto"

    def _classify_intent(
        self,
        question: str,
        has_active_doc: bool,
        history: List[Dict[str, Any]],
        search_mode: str = "auto",
        active_company_name: Optional[str] = None,
    ) -> tuple[str, bool]:
        """Classifies inquiry intent and returns (intent_category, should_web_search)."""
        return self.intent_router.classify(
            question=question,
            has_active_doc=has_active_doc,
            active_company_name=active_company_name,
            history=history,
            search_mode=search_mode,
        )

    def _resolve_follow_up_query(self, question: str, history: List[Dict[str, Any]]) -> str:
        """Rewrites a context-dependent follow-up question using the prior discussion turn."""
        if not history:
            return question

        last_user = ""
        last_asst = ""
        for m in reversed(history):
            role = m.get("role") or m.get("sender") or ""
            text = m.get("content") or m.get("text") or ""
            if not last_asst and role in ("assistant", "ai"):
                last_asst = text[:200]
            elif not last_user and role == "user":
                last_user = text

        if last_user:
            return f"{question} (Context from previous question: '{last_user}')"
        return question

    def process_query(
        self,
        document_id: str,
        question: str,
        user_id: str = "dev_user_123",
        conversation_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 8,
        use_web_search: Optional[bool] = None,
        search_mode: Optional[str] = "auto",
    ) -> ChatResponse:
        """
        Processes user inquiries with intelligent intent routing (Categories A–E):
        - GENERAL_CONVERSATION: direct friendly conversational answer (no vector search or web search)
        - DOCUMENT_QUESTION: grounded RAG hybrid retrieval using uploaded PDF
        - REALTIME_CURRENT: live market quotes and web search discovery
        - MIXED_FINANCIAL: cross-temporal synthesis combining historical PDF facts and current market data
        - OUT_OF_SCOPE: polite domain boundary
        """
        effective_mode = self._resolve_effective_mode(search_mode, use_web_search)

        # 1. Resolve or Create Conversation Thread
        conv = None
        if conversation_id:
            conv = self.conv_service.get_conversation(conversation_id=conversation_id, user_id=user_id)

        active_doc_id = document_id
        has_real_document = bool(active_doc_id and active_doc_id not in ("doc_unknown", "doc_general"))

        if not has_real_document:
            if conv and conv.documentId and conv.documentId not in ("doc_unknown", "doc_general"):
                active_doc_id = conv.documentId
                has_real_document = True
            else:
                user_docs = self.rag_service.document_service.list_user_documents(user_id=user_id)
                if user_docs:
                    active_doc_id = user_docs[-1].documentId
                    has_real_document = True
                else:
                    active_doc_id = "doc_general"

        if not conv:
            conv = self.conv_service.create_conversation(
                user_id=user_id,
                document_id=active_doc_id,
                title=question[:45] + ("..." if len(question) > 45 else "")
            )
        active_conv_id = conv.conversationId

        # 2. Record User Message
        self.conv_service.add_message(
            conversation_id=active_conv_id,
            user_id=user_id,
            role="user",
            content=question
        )

        # 3. Build Conversation History Context
        history_to_supply: List[Dict[str, Any]] = []
        if conv.messages and len(conv.messages) > 1:
            for m in conv.messages[-7:-1]:
                history_to_supply.append({"role": m.role, "content": m.content})
        elif conversation_history:
            history_to_supply = conversation_history

        # 4. Classify Intent & Decide Web Search
        active_company_name = ""
        if has_real_document and active_doc_id not in ("doc_unknown", "doc_general"):
            try:
                doc = self.rag_service.document_service.get_document(active_doc_id, user_id=user_id)
                active_company_name = getattr(doc, "companyName", "") if doc else ""
            except Exception:
                active_company_name = ""

        intent, should_web_search = self._classify_intent(
            question=question,
            has_active_doc=has_real_document,
            history=history_to_supply,
            search_mode=effective_mode,
            active_company_name=active_company_name,
        )
        logger.info(f"FinSight AI Router -> Q: '{question}' | Intent: '{intent}' | Search Mode: '{effective_mode}' | Do Search: {should_web_search}")

        # 5. Route Execution Based on Intent

        # Case 0: EXPLICIT @websearch / Web-Only Mode
        # Works exclusively on AI + Live Web Search. Local document RAG (ChromaDB) is completely bypassed.
        is_web_only = (
            effective_mode == "web_only"
            or bool(re.search(r"(?i)@websearch\b|@web\b", question))
        )
        if is_web_only:
            clean_q = re.sub(r"(?i)@websearch\b|@web\b", "", question).strip()
            if not clean_q:
                clean_q = question.strip()

            logger.info(f"FinSight AI: Executing Pure AI + Web Search (@websearch mode) for query: '{clean_q}'. Local RAG bypassed.")

            # Identify target company or ticker from query
            resolved_ticker = self.web_search_service.resolve_ticker(clean_q)
            company_name = self.web_search_service.extract_company_from_text(clean_q)
            if not company_name and resolved_ticker:
                from .web_search_service import POPULAR_TICKER_MAP
                for k, sym in POPULAR_TICKER_MAP.items():
                    if sym == resolved_ticker and k in clean_q.lower():
                        company_name = k.title()
                        break
                if not company_name:
                    company_name = resolved_ticker.split(".")[0]

            web_context = self.web_search_service.format_web_intelligence_context(
                company_name=company_name or clean_q,
                query=clean_q,
                ticker=resolved_ticker,
            )
            web_sources = self.web_search_service.search_company_web(company_name or clean_q, clean_q, max_results=4)
            market_data = self.web_search_service.get_company_stock_quote(company_name or clean_q, resolved_ticker)

            if not web_context and not market_data:
                fallback_msg = (
                    f"I conducted a live web search for '{clean_q}', but was unable to find verified recent financial news or quotes. "
                    "Please check the company name or topic and try again."
                )
                return self._finalize_response(active_conv_id, user_id, fallback_msg, [])

            prompt = (
                f"Live External Web Intelligence Evidence:\n{web_context}\n\n"
                f"User Question:\n{clean_q}\n\n"
                f"CRITICAL INSTRUCTIONS (AI + WEB SEARCH ONLY — LOCAL RAG BYPASSED):\n"
                f"1. You are running in dedicated @websearch mode. Provide a direct, factual, and comprehensive answer based EXCLUSIVELY on the live web intelligence and market data above.\n"
                f"2. Incorporate clickable Markdown links formatted as [Publisher or Title](URL) within your answer.\n"
                f"3. Conclude with a dedicated section:\n"
                f"   ### 🌐 Verified External Sources & Links\n"
                f"   List each source link as a bullet point with its title/publisher and direct URL so the user can cross-check and independently verify the facts without blindly trusting generated figures.\n"
                f"4. If stock quote information is available, mention the current price, day's percentage change, and quote timestamp in clear language.\n"
                f"5. Do NOT include local PDF document citations or page numbers; this query is served exclusively via live web search."
            )
            ai_answer = self.rag_service.llm_client.generate_response(
                prompt=prompt,
                system_instruction=FINSIGHT_ANALYST_SYSTEM_PROMPT,
                conversation_history=history_to_supply,
                temperature=0.1,
                max_tokens=1000
            )
            return self._finalize_response(
                active_conv_id, user_id, clean_user_facing_response(ai_answer), [],
                web_sources=web_sources,
                market_data=market_data
            )

        # Case 1: GENERAL_CONVERSATION (Greetings, Identity, Capabilities, EBITDA/Ratio definitions)
        if intent == IntentType.GENERAL_CONVERSATION:
            ai_answer = self.rag_service.llm_client.generate_response(
                prompt=question,
                system_instruction=FINSIGHT_CONVERSATIONAL_SYSTEM_PROMPT,
                conversation_history=history_to_supply,
                temperature=0.3,
                max_tokens=650
            )
            return self._finalize_response(active_conv_id, user_id, clean_user_facing_response(ai_answer), [])

        # Case 2: OUT_OF_SCOPE (Non-financial topics)
        if intent == IntentType.OUT_OF_SCOPE:
            out_of_scope_msg = (
                "I am FinSight AI, a financial intelligence assistant. "
                "I specialize in analyzing corporate financial filings, balance sheets, income statements, cash flows, and market trends.\n\n"
                "Please feel free to ask any financial question, request stock intelligence, or upload a financial report (PDF) for verified analysis!"
            )
            return self._finalize_response(active_conv_id, user_id, out_of_scope_msg, [])

        # Case 3: REALTIME_CURRENT (Live Share Prices, News, Market Events)
        if intent == IntentType.REALTIME_CURRENT:
            if effective_mode == "off":
                no_search_msg = (
                    "Live web search is currently turned **OFF**. "
                    "To retrieve real-time stock prices or current market news, switch the search toggle to **Auto** or **On**.\n\n"
                    "If you have an uploaded financial report, I can answer questions regarding reported historical performance."
                )
                return self._finalize_response(active_conv_id, user_id, no_search_msg, [])

            # Prioritize company/ticker mentioned in the user question over the uploaded document
            company_name = self.web_search_service.extract_company_from_text(question)
            resolved_ticker = self.web_search_service.resolve_ticker(question)
            if not company_name and resolved_ticker:
                from .web_search_service import POPULAR_TICKER_MAP
                for k, sym in POPULAR_TICKER_MAP.items():
                    if sym == resolved_ticker and k in question.lower():
                        company_name = k.title()
                        break
                if not company_name:
                    company_name = resolved_ticker.split(".")[0]

            # Fallback to active document's company only if question does not mention an external topic or IPO
            has_external_topic = bool(re.search(r"\b(?:ipo|initial public offering|lot|gmp|grey market|allotment|price band|issue price|share price|stock price|competitor|peer)\b", question, re.IGNORECASE))
            active_mentioned = bool(active_company_name and any(part.lower() in question.lower() for part in active_company_name.split() if len(part) > 3))
            if not company_name and has_real_document and (active_mentioned or not has_external_topic):
                company_name = active_company_name
                if not resolved_ticker:
                    resolved_ticker = self.web_search_service.resolve_ticker(company_name)

            web_context = self.web_search_service.format_web_intelligence_context(
                company_name=company_name or question,
                query=question,
                ticker=resolved_ticker,
            )
            web_sources = self.web_search_service.search_company_web(company_name or question, question, max_results=3)
            market_data = self.web_search_service.get_company_stock_quote(company_name or question, resolved_ticker)

            if not web_context and not market_data:
                fallback_msg = (
                    "I was unable to retrieve verified live market quotes or external news for this query at this time. "
                    "Please verify the company name or ticker symbol and try again."
                )
                return self._finalize_response(active_conv_id, user_id, fallback_msg, [])

            prompt = (
                f"Live Market & External Web Intelligence Evidence:\n{web_context}\n\n"
                f"User Question:\n{question}\n\n"
                f"CRITICAL INSTRUCTIONS:\n"
                f"1. Answer the question directly, accurately, and professionally based on the evidence above.\n"
                f"2. Incorporate clickable Markdown links formatted as [Publisher or Title](URL) within your answer.\n"
                f"3. In addition, conclude with a dedicated section:\n"
                f"   ### 🌐 Verified External Sources & Links\n"
                f"   List each source link as a bullet point with its title/publisher and URL so the user can cross-check and independently verify the facts without blindly trusting generated figures.\n"
                f"4. If stock quote information is available, state the current price, day's percentage change, and quote timestamp in clear language."
            )
            ai_answer = self.rag_service.llm_client.generate_response(
                prompt=prompt,
                system_instruction=FINSIGHT_ANALYST_SYSTEM_PROMPT,
                conversation_history=history_to_supply,
                temperature=0.1,
                max_tokens=900
            )
            return self._finalize_response(
                active_conv_id, user_id, clean_user_facing_response(ai_answer), [],
                web_sources=web_sources,
                market_data=market_data
            )

        # Case 4: Document questions without an uploaded document
        if not has_real_document:
            prompt_guide = (
                "To analyze specific company financial metrics or evaluate reported performance, please select or upload a financial report (PDF) first.\n\n"
                "Once uploaded, I will extract verified balance sheet, P&L, and cash flow figures with exact page citations. "
                "For general finance questions or live market queries, feel free to ask anytime!"
            )
            return self._finalize_response(active_conv_id, user_id, prompt_guide, [])

        # Case 5: Grounded RAG Pipeline (DOCUMENT_QUESTION & MIXED_FINANCIAL)
        rag_query = question
        if q_clean := question.strip().lower():
            if q_clean.startswith(("what about", "why did that", "how about", "and last year")):
                rag_query = self._resolve_follow_up_query(question, history_to_supply)

        cache_key = self.cache_service.build_cache_key(
            "chat_rag",
            user_id=user_id,
            document_id=active_doc_id,
            extra_params={"q": rag_query.strip().lower(), "hist_count": len(history_to_supply), "search": should_web_search}
        )

        cached_rag = self.cache_service.get_cached_result(cache_key) if not should_web_search else None
        if cached_rag:
            rag_output = cached_rag
        else:
            rag_output = self.rag_service.answer_question(
                user_id=user_id,
                document_id=active_doc_id,
                question=rag_query,
                conversation_history=history_to_supply,
                top_k=top_k,
                use_web_search=should_web_search,
            )
            if rag_output and rag_output.get("answer") and not should_web_search:
                self.cache_service.save_result(cache_key, "chat_rag", user_id, [active_doc_id], rag_output)

        page_list = rag_output.get("pages", [])
        section_list = rag_output.get("sections", [])
        filtered_chunks = rag_output.get("retrieved_chunks", [])
        web_sources = rag_output.get("web_sources", [])
        market_data = rag_output.get("market_data")

        structured_sources = []
        for c in filtered_chunks:
            structured_sources.append({
                "page_number": c.get("page_number", 1),
                "section": c.get("section", "General"),
                "snippet": c.get("text", "")[:200],
                "chunk_id": c.get("chunk_id"),
                "similarity_score": c.get("similarity_score", 1.0)
            })

        return self._finalize_response(
            conversation_id=active_conv_id,
            user_id=user_id,
            answer=clean_user_facing_response(rag_output.get("answer", "")),
            structured_sources=structured_sources,
            text_sources=rag_output.get("sources", []),
            page_list=page_list,
            section_list=section_list,
            filtered_chunks=filtered_chunks,
            web_sources=web_sources,
            market_data=market_data,
        )

    def process_query_stream(
        self,
        document_id: str,
        question: str,
        user_id: str = "dev_user_123",
        conversation_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 8,
        use_web_search: Optional[bool] = None,
        search_mode: Optional[str] = "auto",
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streaming endpoint executing real-time Server-Sent Events (SSE).
        Streams tokens progressively (< 350ms TTFT) without exposing developer/technical implementation artifacts.
        """
        effective_mode = self._resolve_effective_mode(search_mode, use_web_search)

        conv = None
        if conversation_id:
            conv = self.conv_service.get_conversation(conversation_id=conversation_id, user_id=user_id)

        active_doc_id = document_id
        has_real_document = bool(active_doc_id and active_doc_id not in ("doc_unknown", "doc_general"))

        if not has_real_document:
            if conv and conv.documentId and conv.documentId not in ("doc_unknown", "doc_general"):
                active_doc_id = conv.documentId
                has_real_document = True
            else:
                user_docs = self.rag_service.document_service.list_user_documents(user_id=user_id)
                if user_docs:
                    active_doc_id = user_docs[-1].documentId
                    has_real_document = True
                else:
                    active_doc_id = "doc_general"

        if not conv:
            conv = self.conv_service.create_conversation(
                user_id=user_id,
                document_id=active_doc_id,
                title=question[:45] + ("..." if len(question) > 45 else "")
            )
        active_conv_id = conv.conversationId

        self.conv_service.add_message(
            conversation_id=active_conv_id,
            user_id=user_id,
            role="user",
            content=question
        )

        history_to_supply: List[Dict[str, Any]] = []
        if conv.messages and len(conv.messages) > 1:
            for m in conv.messages[-7:-1]:
                history_to_supply.append({"role": m.role, "content": m.content})
        elif conversation_history:
            history_to_supply = conversation_history

        active_company_name = ""
        if has_real_document and active_doc_id not in ("doc_unknown", "doc_general"):
            try:
                doc = self.rag_service.document_service.get_document(active_doc_id, user_id=user_id)
                active_company_name = getattr(doc, "companyName", "") if doc else ""
            except Exception:
                active_company_name = ""

        intent, should_web_search = self._classify_intent(
            question=question,
            has_active_doc=has_real_document,
            history=history_to_supply,
            search_mode=effective_mode,
            active_company_name=active_company_name,
        )

        is_web_only = (
            effective_mode == "web_only"
            or bool(re.search(r"(?i)@websearch\b|@web\b", question))
        )

        # Check if query targets an external company or external market/IPO topic
        query_company = self.web_search_service.extract_company_from_text(question)
        is_external_company = bool(
            query_company and active_company_name and query_company.lower() not in active_company_name.lower()
        )
        has_external_topic = bool(
            re.search(r"\b(?:ipo|initial public offering|lot|gmp|grey market|allotment|price band|issue price|stock price|share price)\b", question, re.IGNORECASE)
        )

        # For @websearch mode, external inquiries, conversational turns, out-of-scope, real-time market queries, or questions without an uploaded document:
        if (
            is_web_only
            or is_external_company
            or has_external_topic
            or intent in (IntentType.GENERAL_CONVERSATION, IntentType.OUT_OF_SCOPE, IntentType.REALTIME_CURRENT)
            or (not has_real_document and intent == IntentType.DOCUMENT_QUESTION)
        ):
            resp = self.process_query(
                document_id=active_doc_id,
                question=question,
                user_id=user_id,
                conversation_id=active_conv_id,
                conversation_history=history_to_supply,
                top_k=top_k,
                use_web_search=use_web_search,
                search_mode=effective_mode,
            )
            yield {
                "type": "start",
                "conversationId": active_conv_id,
                "sources": resp.sources,
                "pages": resp.pages,
                "web_sources": resp.web_sources,
                "market_data": resp.market_data,
            }
            # Stream response in natural word chunks
            words = resp.answer.split(" ")
            for idx, word in enumerate(words):
                piece = word + (" " if idx < len(words) - 1 else "")
                yield {
                    "type": "token",
                    "content": piece,
                }
            yield {
                "type": "done",
                "full_answer": resp.answer,
                "conversationId": active_conv_id,
                "sources": resp.sources,
                "pages": resp.pages,
                "web_sources": resp.web_sources,
                "market_data": resp.market_data,
            }
            return

        rag_query = question
        if intent == "FOLLOW_UP":
            rag_query = self._resolve_follow_up_query(question, history_to_supply)

        final_answer = ""
        final_sources = []
        final_pages = []

        for item in self.rag_service.answer_question_stream(
            user_id=user_id,
            document_id=active_doc_id,
            question=rag_query,
            conversation_history=history_to_supply,
            top_k=top_k,
            use_web_search=should_web_search,
        ):
            item["conversationId"] = active_conv_id
            if item.get("type") == "done":
                final_answer = clean_user_facing_response(item.get("full_answer", ""))
                item["full_answer"] = final_answer
                final_sources = item.get("sources", [])
                final_pages = item.get("pages", [])
            yield item

        # Record assistant answer in conversation history
        if final_answer:
            self.conv_service.add_message(
                conversation_id=active_conv_id,
                user_id=user_id,
                role="assistant",
                content=final_answer,
                sources=[{"page_number": p} for p in final_pages] if final_pages else []
            )

    def _finalize_response(
        self,
        conversation_id: str,
        user_id: str,
        answer: str,
        structured_sources: List[Dict[str, Any]],
        text_sources: Optional[List[str]] = None,
        page_list: Optional[List[int]] = None,
        section_list: Optional[List[str]] = None,
        filtered_chunks: Optional[List[Dict[str, Any]]] = None,
        web_sources: Optional[List[Dict[str, str]]] = None,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> ChatResponse:
        """
        Saves the assistant reply to Firestore and builds the standardized ChatResponse schema.
        """
        clean_ans = clean_user_facing_response(answer)
        self.conv_service.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=clean_ans,
            sources=structured_sources or []
        )

        citation_objects = [
            Citation(
                page_number=s.get("page_number", 1),
                section=s.get("section", "General"),
                snippet=s.get("snippet", ""),
                similarity_score=s.get("similarity_score", 1.0)
            )
            for s in structured_sources
        ]

        return ChatResponse(
            conversation_id=conversation_id,
            conversationId=conversation_id,
            answer=clean_ans,
            citations=citation_objects,
            sources=text_sources or [],
            pages=page_list or [],
            sections=section_list or [],
            retrieved_chunks=filtered_chunks or [],
            web_sources=web_sources or [],
            market_data=market_data,
            is_grounded=len(page_list or []) > 0 or len(web_sources or []) > 0
        )
