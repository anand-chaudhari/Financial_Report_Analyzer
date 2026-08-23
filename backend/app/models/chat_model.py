from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class ChatMessageModel:
    """Domain model representing a single chat message."""
    id: str
    chat_id: str
    sender: str  # user | assistant | system
    content: str
    citations: List[Dict[str, Any]] = field(default_factory=list)
    is_grounded: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "sender": self.sender,
            "content": self.content,
            "citations": self.citations,
            "is_grounded": self.is_grounded,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
        }


@dataclass
class ChatSessionModel:
    """Domain model representing a chat conversation session for a report."""
    id: str
    report_id: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    messages: List[ChatMessageModel] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "report_id": self.report_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "last_updated": self.last_updated.isoformat() if isinstance(self.last_updated, datetime) else self.last_updated,
        }
