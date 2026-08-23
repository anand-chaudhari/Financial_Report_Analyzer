from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Citation(BaseModel):
    page_number: int
    snippet: str
    chunk_id: Optional[str] = None
    similarity_score: Optional[float] = None


class ChatMessageItem(BaseModel):
    id: Optional[str] = None
    sender: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    citations: List[Citation] = Field(default_factory=list)
    is_grounded: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    document_id: Optional[str] = None
    report_id: Optional[str] = None
    question: str = Field(..., min_length=2, max_length=2000)
    conversation_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    top_k: Optional[int] = 4

    @property
    def target_document_id(self) -> str:
        doc_id = self.document_id or self.report_id
        if not doc_id:
            raise ValueError("Either document_id or report_id must be provided.")
        return doc_id


class ChatQueryRequest(ChatRequest):
    """Backward compatible alias for ChatRequest."""
    pass


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)
    pages: List[int] = Field(default_factory=list)
    sections: List[str] = Field(default_factory=list)
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    is_grounded: bool = True
    source_found: bool = True


class ChatQueryResponse(ChatResponse):
    """Backward compatible alias for ChatResponse."""
    pass


class ChatHistoryResponse(BaseModel):
    report_id: str
    messages: List[ChatMessageItem] = Field(default_factory=list)
