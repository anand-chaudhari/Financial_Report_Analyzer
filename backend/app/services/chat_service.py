import uuid
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..schemas.chat_schema import ChatResponse, ChatMessageItem, Citation
from ..rag.rag_service import RAGService
from ..rag.prompts import FINSIGHT_CONVERSATIONAL_SYSTEM_PROMPT
from ..services.conversation_service import ConversationService
from .cache_service import get_ai_cache_service
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class ChatService:
    """
    Context-Aware FinSight AI Chat Service.
    Implements modular intent classification layer and persistent RAG query caching.
    """

    def __init__(
        self,
        rag_service: Optional[RAGService] = None,
        conv_service: Optional[ConversationService] = None
    ):
        self.rag_service = rag_service or RAGService()
        self.conv_service = conv_service or ConversationService()
        self.cache_service = get_ai_cache_service()

    def _classify_intent(
        self,
        question: str,
        has_active_doc: bool,
        history: List[Dict[str, Any]],
    ) -> str:
        """
        Detects user intent before query execution:
        - GREETING: Greetings, introductory questions, identity, capabilities.
        - GENERAL_FINANCE: Financial definitions/theories without report dependencies.
        - INVESTMENT_ANALYSIS: Inquiries about investing, buying/selling stocks.
        - FOLLOW_UP: Context-dependent follow-up queries referencing prior discussion.
        - OUT_OF_SCOPE: Non-finance and unrelated conversational queries.
        - DOCUMENT_QUESTION: Inquiries requiring factual extraction from the uploaded report.
        """
        q_clean = question.strip().lower()
        q_words = re.findall(r"\b\w+\b", q_clean)

        # 1. GREETING (Greetings, Polite Casual, Identity, Capabilities)
        greeting_words = {"hi", "hello", "hey", "hola", "greetings", "sup"}
        if len(q_words) <= 3 and any(w in greeting_words for w in q_words):
            return "GREETING"

        casual_phrases = [
            "good morning", "good afternoon", "good evening", "how are you",
            "who are you", "what can you do", "what is your name", "tell me about yourself",
            "what are your features", "who built you", "thank you", "thanks", "bye", "goodbye",
            "help me", "what is finsight", "what is finsight ai", "what do you do"
        ]
        if any(phrase in q_clean for phrase in casual_phrases):
            return "GREETING"

        # 2. OUT_OF_SCOPE (Completely unrelated topics like weather, cooking, trivia, poetry)
        out_of_scope_triggers = [
            "weather", "recipe", "write a poem", "write a song", "tell me a joke",
            "who won the", "football", "cricket match", "movie recommendation", "sing a song",
            "translate to french", "translate to spanish", "write a python script to scrape"
        ]
        if any(t in q_clean for t in out_of_scope_triggers):
            return "OUT_OF_SCOPE"

        # 3. INVESTMENT_ANALYSIS (Investment suitability, Buy/Sell/Hold questions)
        investment_triggers = [
            "can i invest", "should i invest", "is this a good investment", "should i buy",
            "should i sell", "is this stock good", "is this a growth stock", "buy or sell",
            "would you recommend investing", "is it safe to invest"
        ]
        if any(t in q_clean for t in investment_triggers):
            return "INVESTMENT_ANALYSIS"

        # 4. FOLLOW_UP (Context-dependent follow-up questions referencing prior turn)
        follow_up_triggers = [
            "what about last year", "what about", "why did it", "why did that", "how about",
            "and last year", "compare it with", "compare with previous", "why did revenue",
            "why did profit", "explain that", "what were the risks of that", "how much did it decrease",
            "how much did it increase", "is it increasing", "why so", "and the previous year"
        ]
        if history and len(history) > 0:
            if any(trig in q_clean for trig in follow_up_triggers) or q_clean.startswith(("and ", "what about", "why ")):
                return "FOLLOW_UP"

        # 5. GENERAL_FINANCE (General financial theory, formulas, definitions)
        general_concept_triggers = [
            "what is ebitda", "what is pe ratio", "what is p/e ratio", "explain working capital",
            "what is roe", "what is roa", "what is roce", "what is free cash flow", "what is fcf",
            "difference between capex and opex", "difference between pbt and pat", "what is gross margin",
            "what is operating margin", "what is debt to equity", "what is current ratio",
            "what is quick ratio", "what is market cap", "what is dividend yield",
            "what is book value", "what is goodwill", "what is depreciation", "what is amortization",
            "what is cash flow statement", "what is balance sheet", "what is income statement",
            "define ebitda", "formula for ebitda", "how to calculate ebitda", "explain ebitda"
        ]
        if any(trig in q_clean for trig in general_concept_triggers) and "this report" not in q_clean and "this company" not in q_clean:
            return "GENERAL_FINANCE"

        # 6. DOCUMENT_QUESTION (Default for financial data inquiries)
        return "DOCUMENT_QUESTION"

    def _resolve_follow_up_query(self, question: str, history: List[Dict[str, Any]]) -> str:
        """
        Rewrites a context-dependent follow-up question using the prior discussion turn
        so vector search retrieves the correct topic from the financial filing.
        """
        if not history:
            return question

        last_assistant_msg = ""
        last_user_msg = ""
        for m in reversed(history):
            role = m.get("role") or m.get("sender") or ""
            content = m.get("content") or m.get("text") or ""
            if role in ("assistant", "ai") and not last_assistant_msg:
                last_assistant_msg = content[:200]
            elif role == "user" and not last_user_msg:
                last_user_msg = content

        if last_user_msg:
            return f"[Context: {last_user_msg}] Follow-up inquiry: {question}"
        return question

    def process_query(
        self,
        document_id: Optional[str],
        question: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 8,
    ) -> ChatResponse:
        """
        Processes user inquiries with intelligent intent routing:
        - GREETING / GENERAL_FINANCE / OUT_OF_SCOPE -> direct conversational LLM response (no vector search)
        - DOCUMENT_QUESTION / INVESTMENT_ANALYSIS / FOLLOW_UP:
          - If report uploaded -> grounded RAG with verifiable page citations
          - If NO report uploaded -> polite prompt requesting report upload
        """
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
        elif document_id and conv.documentId != document_id:
            conv.documentId = document_id
            try:
                if self.conv_service.firestore_db:
                    self.conv_service.firestore_db.collection("conversations").document(conv.conversationId).update({
                        "documentId": document_id,
                        "updatedAt": datetime.utcnow().isoformat()
                    })
            except Exception as ex:
                logger.warning(f"Could not update conversation documentId in Firestore: {str(ex)}")

        active_conv_id = conv.conversationId

        # 2. Record User Question in Firestore
        self.conv_service.add_message(
            conversation_id=active_conv_id,
            user_id=user_id,
            role="user",
            content=question
        )

        # 3. Build Conversation History Context
        history_to_supply: List[Dict[str, Any]] = []
        if conv.messages and len(conv.messages) > 0:
            for m in conv.messages[-6:]:
                history_to_supply.append({"role": m.role, "content": m.content})
        elif conversation_history:
            history_to_supply = conversation_history

        # 4. Classify Intent
        intent = self._classify_intent(
            question=question,
            has_active_doc=has_real_document,
            history=history_to_supply
        )
        logger.info(f"FinSight AI Intent Classifier -> Question: '{question}' | Detected Intent: '{intent}'")

        # 5. Route Execution Based on Intent

        # Case 1: GREETING (Greetings, Identity, Capabilities)
        if intent == "GREETING":
            ai_answer = self.rag_service.llm_client.generate_response(
                prompt=question,
                system_instruction=FINSIGHT_CONVERSATIONAL_SYSTEM_PROMPT,
                conversation_history=history_to_supply,
                temperature=0.4,
                max_tokens=500
            )
            return self._finalize_response(active_conv_id, user_id, ai_answer, [])

        # Case 2: GENERAL_FINANCE (EBITDA, Ratios, Formulas, Definitions)
        elif intent == "GENERAL_FINANCE":
            ai_answer = self.rag_service.llm_client.generate_response(
                prompt=f"Explain the following financial concept clearly and concisely with standard definitions and formulas:\n\n{question}",
                system_instruction=FINSIGHT_CONVERSATIONAL_SYSTEM_PROMPT,
                conversation_history=history_to_supply,
                temperature=0.2,
                max_tokens=750
            )
            return self._finalize_response(active_conv_id, user_id, ai_answer, [])

        # Case 3: OUT_OF_SCOPE (Non-financial topics)
        elif intent == "OUT_OF_SCOPE":
            out_of_scope_msg = (
                "I am FinSight AI, a specialized financial report analysis assistant. "
                "I focus on corporate filings, balance sheets, income statements, cash flows, and financial metric extraction.\n\n"
                "Please feel free to ask any financial concept question or upload a corporate filing PDF for in-depth analysis!"
            )
            return self._finalize_response(active_conv_id, user_id, out_of_scope_msg, [])

        # Case 4: Document questions without an uploaded document
        elif not has_real_document:
            prompt_guide = (
                "To analyze specific company financial data or evaluate corporate performance, please upload a financial report (PDF) first.\n\n"
                "Once uploaded, I will extract verified balance sheet, P&L, and cash flow metrics with exact page citations."
            )
            return self._finalize_response(active_conv_id, user_id, prompt_guide, [])

        # Case 5: Grounded RAG Pipeline (DOCUMENT_QUESTION, INVESTMENT_ANALYSIS, FOLLOW_UP)
        else:
            rag_query = question
            if intent == "FOLLOW_UP":
                rag_query = self._resolve_follow_up_query(question, history_to_supply)

            cache_key = self.cache_service.build_cache_key(
                "chat_rag",
                user_id=user_id,
                document_id=active_doc_id,
                extra_params={"q": rag_query.strip().lower(), "hist_count": len(history_to_supply)}
            )

            cached_rag = self.cache_service.get_cached_result(cache_key)
            if cached_rag:
                rag_output = cached_rag
            else:
                rag_output = self.rag_service.answer_question(
                    user_id=user_id,
                    document_id=active_doc_id,
                    question=rag_query,
                    conversation_history=history_to_supply,
                    top_k=top_k,
                )
                if rag_output and rag_output.get("answer"):
                    self.cache_service.save_result(cache_key, "chat_rag", user_id, [active_doc_id], rag_output)

            page_list = rag_output.get("pages", [])
            section_list = rag_output.get("sections", [])
            text_sources = rag_output.get("sources", [])
            raw_chunks = rag_output.get("retrieved_chunks", [])

            structured_sources: List[Dict[str, Any]] = []
            filtered_chunks: List[Dict[str, Any]] = []

            if page_list and len(page_list) > 0:
                target_page_set = set(page_list)
                for c in raw_chunks:
                    p_num = c.get("page_number", 1)
                    if p_num in target_page_set:
                        filtered_chunks.append(c)
                        structured_sources.append({
                            "page_number": p_num,
                            "section": c.get("section", "General"),
                            "document_name": c.get("file_name", "document.pdf"),
                            "snippet": c.get("text", "")[:300],
                            "similarity_score": c.get("similarity_score")
                        })

                if not structured_sources:
                    for idx, p in enumerate(page_list):
                        structured_sources.append({
                            "page_number": p,
                            "section": section_list[idx] if idx < len(section_list) else "Financial Statement",
                            "document_name": "report.pdf",
                            "snippet": text_sources[idx] if idx < len(text_sources) else ""
                        })

            return self._finalize_response(
                conversation_id=active_conv_id,
                user_id=user_id,
                answer=rag_output["answer"],
                structured_sources=structured_sources,
                text_sources=text_sources,
                page_list=page_list,
                section_list=section_list,
                filtered_chunks=filtered_chunks
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
        filtered_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> ChatResponse:
        """
        Saves the assistant reply to Firestore and builds the standardized ChatResponse schema.
        """
        # Save assistant message in Firestore conversation history
        self.conv_service.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=answer,
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
            answer=answer,
            citations=citation_objects,
            sources=text_sources or [],
            pages=page_list or [],
            sections=section_list or [],
            retrieved_chunks=filtered_chunks or [],
            is_grounded=len(page_list or []) > 0
        )
