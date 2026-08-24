import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..models.chat_model import ChatMessageModel, ChatSessionModel
from ..schemas.chat_schema import ChatResponse, ChatMessageItem, Citation
from ..rag.rag_service import RAGService
from ..firebase.firestore import get_firestore_client
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

_in_memory_chats: Dict[str, List[ChatMessageItem]] = {}


class ChatService:
    """Service orchestrating chat sessions, RAG queries, and message persistence."""

    def __init__(self, rag_service: Optional[RAGService] = None):
        self.rag_service = rag_service or RAGService()
        self.firestore_db = get_firestore_client()

    def process_query(
        self,
        document_id: str,
        question: str,
        user_id: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 8,
    ) -> ChatResponse:
        """Executes RAG question answering and records conversation history."""
        # 1. Fetch recent history if not explicitly provided
        if conversation_history is None:
            raw_history = self.get_history(document_id, user_id)
            conversation_history = [
                {"sender": item.sender, "text": item.content} for item in raw_history[-6:]
            ]

        # 2. Record user question
        user_msg = ChatMessageItem(
            id=str(uuid.uuid4()),
            sender="user",
            content=question,
            citations=[],
            is_grounded=True,
            timestamp=datetime.utcnow(),
        )
        self._append_message(document_id, user_msg)

        # 3. Query RAG engine
        rag_output = self.rag_service.answer_question(
            user_id=user_id,
            document_id=document_id,
            question=question,
            conversation_history=conversation_history,
            top_k=top_k,
        )

        citations_list = [
            Citation(page_number=p, snippet=s)
            for p, s in zip(rag_output.get("pages", []), rag_output.get("sources", []))
        ]

        chat_response = ChatResponse(
            answer=rag_output["answer"],
            sources=rag_output.get("sources", []),
            pages=rag_output.get("pages", []),
            sections=rag_output.get("sections", []),
            retrieved_chunks=rag_output.get("retrieved_chunks", []),
            citations=citations_list,
            is_grounded=True,
            source_found=bool(rag_output.get("sources")),
        )

        # 4. Record assistant response
        assistant_msg = ChatMessageItem(
            id=str(uuid.uuid4()),
            sender="assistant",
            content=chat_response.answer,
            citations=citations_list,
            is_grounded=chat_response.is_grounded,
            timestamp=datetime.utcnow(),
        )
        self._append_message(document_id, assistant_msg)

        return chat_response

    def get_history(self, report_id: str, user_id: str) -> List[ChatMessageItem]:
        """Retrieves conversation history for a given report/document."""
        if self.firestore_db:
            try:
                docs = (
                    self.firestore_db.collection("chats")
                    .document(report_id)
                    .collection("messages")
                    .order_by("timestamp")
                    .stream()
                )
                return [ChatMessageItem(**doc.to_dict()) for doc in docs]
            except Exception as e:
                logger.error(f"Firestore get_history error: {str(e)}")

        return _in_memory_chats.get(report_id, [])

    def clear_history(self, report_id: str, user_id: str) -> bool:
        """Clears chat history for a report."""
        if report_id in _in_memory_chats:
            _in_memory_chats[report_id] = []
        return True

    def _append_message(self, report_id: str, message: ChatMessageItem) -> None:
        """Appends a message to chat history."""
        if report_id not in _in_memory_chats:
            _in_memory_chats[report_id] = []
        _in_memory_chats[report_id].append(message)

        if self.firestore_db:
            try:
                self.firestore_db.collection("chats").document(report_id).collection("messages").document(message.id).set(
                    message.model_dump()
                )
            except Exception as e:
                logger.error(f"Firestore append message error: {str(e)}")
