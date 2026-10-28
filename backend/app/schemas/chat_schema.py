from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Citation(BaseModel):
    page_number: int
    snippet: str
    chunk_id: Optional[str] = None
    similarity_score: Optional[float] = None
    section: Optional[str] = None
    document_name: Optional[str] = None
    is_verified: bool = True


class ChatMessageItem(BaseModel):
    id: Optional[str] = None
    sender: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    citations: List[Citation] = Field(default_factory=list)
    is_grounded: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    conversationId: Optional[str] = None
    document_id: Optional[str] = None
    documentId: Optional[str] = None
    report_id: Optional[str] = None
    question: str = Field(..., min_length=2, max_length=2000)
    conversation_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    top_k: Optional[int] = 8
    use_web_search: Optional[bool] = None
    useWebSearch: Optional[bool] = None
    search_mode: Optional[str] = "auto"
    searchMode: Optional[str] = None

    @property
    def target_conversation_id(self) -> Optional[str]:
        return self.conversation_id or self.conversationId

    @property
    def target_document_id(self) -> Optional[str]:
        return self.document_id or self.documentId or self.report_id

    @property
    def target_search_mode(self) -> str:
        explicit_mode = self.search_mode or self.searchMode
        if explicit_mode and str(explicit_mode).strip().lower() in ("auto", "on", "off", "web_only", "@websearch"):
            _val = str(explicit_mode).strip().lower()
            return "web_only" if _val in ("web_only", "@websearch") else _val

        if self.use_web_search is True or self.useWebSearch is True:
            return "on"
        if self.use_web_search is False or self.useWebSearch is False:
            return "off"
        return "auto"

    @property
    def target_web_search(self) -> bool:
        return self.target_search_mode in ("on", "web_only")


class ChatQueryRequest(ChatRequest):
    """Backward compatible alias for ChatRequest."""
    pass


class ChatResponse(BaseModel):
    conversationId: Optional[str] = None
    messageId: Optional[str] = None
    answer: str
    sources: List[str] = Field(default_factory=list)
    pages: List[int] = Field(default_factory=list)
    sections: List[str] = Field(default_factory=list)
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    web_sources: List[Dict[str, str]] = Field(default_factory=list)
    market_data: Optional[Dict[str, Any]] = None
    citations: List[Citation] = Field(default_factory=list)
    is_grounded: bool = True
    source_found: bool = True


class ChatQueryResponse(ChatResponse):
    """Backward compatible alias for ChatResponse."""
    pass


class ChatHistoryResponse(BaseModel):
    report_id: str
    messages: List[ChatMessageItem] = Field(default_factory=list)
