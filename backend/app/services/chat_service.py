import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..models.chat_model import ChatMessageModel, ChatSessionModel
from ..schemas.chat_schema import ChatQueryResponse, ChatMessageItem
from ..rag.pipeline import RAGPipeline
from ..firebase.firestore import get_firestore_client
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

_in_memory_chats: Dict[str, List[ChatMessageItem]] = {}


class ChatService:
    """Service orchestrating chat sessions, RAG queries, and message persistence."""

    def __init__(self):
        self.rag_pipeline = RAGPipeline()
        self.firestore_db = get_firestore_client()

    def process_query(
        self,
        report_id: str,
        question: str,
        user_id: str,
        top_k: int = 4
    ) -> ChatQueryResponse:
        """Executes RAG question answering and records conversation history."""
        # 1. Record user question
        user_msg = ChatMessageItem(
            id=str(uuid.uuid4()),
            sender="user",
            content=question,
            citations=[],
            is_grounded=True,
            timestamp=datetime.utcnow()
        )
        self._append_message(report_id, user_msg)

        # 2. Query RAG pipeline
        rag_response = self.rag_pipeline.answer_query(
            report_id=report_id,
            question=question,
            user_id=user_id,
            top_k=top_k
        )

        # 3. Record assistant response
        assistant_msg = ChatMessageItem(
            id=str(uuid.uuid4()),
            sender="assistant",
            content=rag_response.answer,
            citations=rag_response.citations,
            is_grounded=rag_response.is_grounded,
            timestamp=datetime.utcnow()
        )
        self._append_message(report_id, assistant_msg)

        return rag_response

    def get_history(self, report_id: str, user_id: str) -> List[ChatMessageItem]:
        """Retrieves conversation history for a given report."""
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
