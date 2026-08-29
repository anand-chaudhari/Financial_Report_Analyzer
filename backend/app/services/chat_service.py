import uuid
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..schemas.chat_schema import ChatResponse, ChatMessageItem, Citation
from ..rag.rag_service import RAGService
from ..rag.prompts import FINSIGHT_CONVERSATIONAL_SYSTEM_PROMPT
from ..services.conversation_service import ConversationService
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class ChatService:
    """Service orchestrating context-aware chat sessions, intent detection, persistent Firestore conversations, and grounded RAG."""

    def __init__(
        self,
        rag_service: Optional[RAGService] = None,
        conv_service: Optional[ConversationService] = None
    ):
        self.rag_service = rag_service or RAGService()
        self.conv_service = conv_service or ConversationService()

    def _classify_intent(
        self,
        question: str,
        has_active_doc: bool,
        history: List[Dict[str, Any]],
    ) -> str:
        """
        Determines user intent before answering:
        1. CONVERSATIONAL (Greetings, Casual, Capabilities, Thanks)
        2. FINANCIAL_CONCEPT (General finance/accounting definitions without report dependency)
        3. FOLLOW_UP (Context-dependent follow-up questions referencing prior turn)
        4. REPORT_NO_DOC (Company/report inquiry but no document uploaded)
        5. REPORT_RAG (Grounded financial analysis of uploaded corporate filing)
        """
        q_clean = question.strip().lower()
        q_words = re.findall(r"\b\w+\b", q_clean)

        # 1. Greetings, Casual Politeness & Identity
        greeting_words = {"hi", "hello", "hey", "hola", "greetings"}
        if len(q_words) <= 3 and any(w in greeting_words for w in q_words):
            return "CONVERSATIONAL"

        casual_phrases = [
            "good morning", "good afternoon", "good evening", "how are you",
            "who are you", "what can you do", "what is your name", "tell me about yourself",
            "what are your features", "who built you", "thank you", "thanks", "bye", "goodbye",
            "help me", "what is finsight", "what is finsight ai"
        ]
        if any(phrase in q_clean for phrase in casual_phrases):
            return "CONVERSATIONAL"

        # 2. Context-Dependent Follow-Up Queries
        follow_up_triggers = [
            "what about", "why did it", "why did that", "how about", "and last year",
            "what about last year", "compare it with", "compare with previous",
            "why did revenue", "why did profit", "explain that", "what were the risks of that",
            "how much did it decrease", "how much did it increase", "is it increasing", "why so"
        ]
        if history and (len(q_words) <= 7 or any(trig in q_clean for trig in follow_up_triggers)):
            if any(trig in q_clean for trig in follow_up_triggers) or q_clean.startswith(("and ", "what about", "why ")):
                return "FOLLOW_UP"

        # 3. General Finance Concept Questions (No specific company or filing context)
        general_concept_triggers = [
            "what is ebitda", "what is pe ratio", "what is p/e ratio", "explain working capital",
            "what is roe", "what is roa", "what is roce", "what is free cash flow", "what is fcf",
            "difference between capex and opex", "difference between pbt and pat", "what is gross margin",
            "what is operating margin", "what is debt to equity", "what is current ratio",
            "what is quick ratio", "what is market cap", "what is dividend yield",
            "what is book value", "what is goodwill", "what is depreciation", "what is amortization",
            "what is cash flow statement", "what is balance sheet", "what is income statement"
        ]
        if any(trig in q_clean for trig in general_concept_triggers) and "this report" not in q_clean and "this company" not in q_clean:
            return "FINANCIAL_CONCEPT"

        # 4. Report-Specific Query check
        if not has_active_doc:
            # If user asks for company/report-specific numbers without a document
            return "REPORT_NO_DOC"

        return "REPORT_RAG"

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
            if role == "assistant" and not last_assistant_msg:
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
        - Conversational / Greetings / General Finance Concepts -> direct natural responses (no unnecessary vector search)
        - Company / Filing Inquiries -> full grounded RAG with verifiable page citations
        - Context-aware follow-up question resolution
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

        # Case A: Greetings / Casual / FinSight AI Capabilities
        if intent == "CONVERSATIONAL":
            ai_answer = self.rag_service.llm_client.generate_response(
                prompt=question,
                system_instruction=FINSIGHT_CONVERSATIONAL_SYSTEM_PROMPT,
                conversation_history=history_to_supply,
                temperature=0.4,
                max_tokens=500
            )
            return self._finalize_response(active_conv_id, user_id, ai_answer, [])

        # Case B: General Financial Concepts (EBITDA, Ratios, Terminology)
        elif intent == "FINANCIAL_CONCEPT":
            ai_answer = self.rag_service.llm_client.generate_response(
                prompt=f"Explain the following financial concept clearly and concisely with standard formulas or examples:\n\n{question}",
                system_instruction=FINSIGHT_CONVERSATIONAL_SYSTEM_PROMPT,
                conversation_history=history_to_supply,
                temperature=0.2,
                max_tokens=750
            )
            return self._finalize_response(active_conv_id, user_id, ai_answer, [])

        # Case C: Company/Report inquiry without an uploaded report
        elif intent == "REPORT_NO_DOC":
            prompt_guide = (
                "To analyze specific company financial metrics, please upload a corporate financial report (PDF) first.\n\n"
                "Once uploaded, I will parse the balance sheet, profit & loss statement, and cash flows to answer your questions with verified, page-referenced citations."
            )
            return self._finalize_response(active_conv_id, user_id, prompt_guide, [])

        # Case D: Grounded RAG Query (or context-aware follow-up)
        else:
            rag_query = question
            if intent == "FOLLOW_UP":
                rag_query = self._resolve_follow_up_query(question, history_to_supply)

            rag_output = self.rag_service.answer_question(
                user_id=user_id,
                document_id=active_doc_id,
                question=rag_query,
                conversation_history=history_to_supply,
                top_k=top_k,
            )

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
        filtered_chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatResponse:
        """Saves assistant turn to Firestore and formats ChatResponse."""
        assistant_msg = self.conv_service.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=answer,
            sources=structured_sources
        )

        citations_list = [
            Citation(
                page_number=s.get("page_number", 1),
                snippet=s.get("snippet", ""),
                section=s.get("section"),
                document_name=s.get("document_name")
            )
            for s in structured_sources
        ]

        msg_id = getattr(assistant_msg, "messageId", f"msg_{uuid.uuid4().hex[:12]}") if assistant_msg else f"msg_{uuid.uuid4().hex[:12]}"

        pages = page_list or []
        sections = section_list or []
        sources = text_sources or []
        retrieved = filtered_chunks or []

        return ChatResponse(
            conversationId=conversation_id,
            messageId=msg_id,
            answer=answer,
            sources=sources,
            pages=pages,
            sections=sections,
            retrieved_chunks=retrieved,
            citations=citations_list,
            is_grounded=bool(pages),
            source_found=bool(pages),
        )

    def get_history(self, report_id: str, user_id: str) -> List[ChatMessageItem]:
        """Retrieves legacy conversation history for a given report/document."""
        convs = self.conv_service.list_user_conversations(user_id=user_id, document_id=report_id)
        if not convs:
            return []

        messages = self.conv_service.get_conversation_messages(conversation_id=convs[0].conversationId, user_id=user_id)
        return [
            ChatMessageItem(
                id=m.messageId,
                sender=m.role,
                content=m.content,
                citations=[
                    Citation(page_number=s.get("page_number", 1), snippet=s.get("snippet", ""))
                    for s in m.sources
                ]
            )
            for m in messages
        ]

    def clear_history(self, report_id: str, user_id: str) -> bool:
        """Clears conversation history for a report."""
        convs = self.conv_service.list_user_conversations(user_id=user_id, document_id=report_id)
        for c in convs:
            self.conv_service.delete_conversation(conversation_id=c.conversationId, user_id=user_id)
        return True
