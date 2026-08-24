from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class MessageModel:
    """Domain model representing a single message in a conversation."""
    messageId: str
    conversationId: str
    userId: str
    role: str  # 'user' | 'assistant'
    content: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    createdAt: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messageId": self.messageId,
            "conversationId": self.conversationId,
            "userId": self.userId,
            "role": self.role,
            "content": self.content,
            "sources": self.sources,
            "createdAt": self.createdAt,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageModel":
        return cls(
            messageId=data.get("messageId") or data.get("id") or "",
            conversationId=data.get("conversationId") or data.get("chat_id") or "",
            userId=data.get("userId") or data.get("user_id") or "",
            role=data.get("role") or data.get("sender") or "user",
            content=data.get("content") or data.get("text") or "",
            sources=data.get("sources") or data.get("citations") or [],
            createdAt=data.get("createdAt") or data.get("timestamp") or datetime.utcnow().isoformat(),
        )


@dataclass
class ConversationModel:
    """Domain model representing a persistent conversation thread."""
    conversationId: str
    userId: str
    documentId: str
    title: str
    createdAt: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updatedAt: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    messages: List[MessageModel] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversationId": self.conversationId,
            "userId": self.userId,
            "documentId": self.documentId,
            "title": self.title,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationModel":
        return cls(
            conversationId=data.get("conversationId") or data.get("id") or "",
            userId=data.get("userId") or data.get("user_id") or "",
            documentId=data.get("documentId") or data.get("report_id") or "",
            title=data.get("title") or "Financial Analysis",
            createdAt=data.get("createdAt") or data.get("created_at") or datetime.utcnow().isoformat(),
            updatedAt=data.get("updatedAt") or data.get("last_updated") or datetime.utcnow().isoformat(),
            messages=[],
        )
