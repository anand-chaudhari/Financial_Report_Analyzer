import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..schemas.chat_schema import ChatResponse, ChatMessageItem, Citation
from ..rag.rag_service import RAGService
from ..services.conversation_service import ConversationService
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class ChatService:
    """Service orchestrating chat sessions, persistent Firestore conversations, RAG queries, and message persistence."""

    def __init__(
        self,
        rag_service: Optional[RAGService] = None,
        conv_service: Optional[ConversationService] = None
    ):
        self.rag_service = rag_service or RAGService()
        self.conv_service = conv_service or ConversationService()

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
        Executes grounded RAG Q&A and persists user question & AI answer with source metadata to Firestore.
        Enforces strict user ownership checks and correct document binding.
        """
        # 1. Resolve or Create Conversation Thread
        conv = None
        if conversation_id:
            conv = self.conv_service.get_conversation(conversation_id=conversation_id, user_id=user_id)

        # Priority resolution for active_doc_id:
        # 1st priority: document_id explicitly requested by client in UI dropdown
        # 2nd priority: conv.documentId if valid
        # 3rd priority: user's most recently uploaded document
        active_doc_id = document_id
        if not active_doc_id or active_doc_id in ("doc_unknown", "doc_general"):
            if conv and conv.documentId and conv.documentId not in ("doc_unknown", "doc_general"):
                active_doc_id = conv.documentId
            else:
                user_docs = self.rag_service.document_service.list_user_documents(user_id=user_id)
                if user_docs:
                    active_doc_id = user_docs[-1].documentId
                else:
                    active_doc_id = "doc_general"

        if not conv:
            conv = self.conv_service.create_conversation(
                user_id=user_id,
                document_id=active_doc_id,
                title=question[:45] + ("..." if len(question) > 45 else "")
            )
        elif document_id and conv.documentId != document_id:
            # Bind conversation thread to current target document
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

        # 3. Supply History to RAG Engine
        history_to_supply: List[Dict[str, Any]] = []
        if conv.messages and len(conv.messages) > 0:
            for m in conv.messages[-6:]:
                history_to_supply.append({"role": m.role, "content": m.content})
        elif conversation_history:
            history_to_supply = conversation_history

        # 4. Execute RAG Question Answering Engine
        rag_output = self.rag_service.answer_question(
            user_id=user_id,
            document_id=active_doc_id,
            question=question,
            conversation_history=history_to_supply,
            top_k=top_k,
        )

        # 5. Format Structured Sources & Citations strictly for verified cited pages
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

            # If filtered_chunks is empty but page_list exists, create entries from page_list
            if not structured_sources:
                for idx, p in enumerate(page_list):
                    structured_sources.append({
                        "page_number": p,
                        "section": section_list[idx] if idx < len(section_list) else "Financial Statement",
                        "document_name": "report.pdf",
                        "snippet": text_sources[idx] if idx < len(text_sources) else ""
                    })

        # 6. Save AI Answer & Source Metadata to Firestore
        assistant_msg = self.conv_service.add_message(
            conversation_id=active_conv_id,
            user_id=user_id,
            role="assistant",
            content=rag_output["answer"],
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

        return ChatResponse(
            conversationId=active_conv_id,
            messageId=msg_id,
            answer=rag_output["answer"],
            sources=text_sources,
            pages=page_list,
            sections=section_list,
            retrieved_chunks=filtered_chunks,
            citations=citations_list,
            is_grounded=bool(page_list),
            source_found=bool(page_list),
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
