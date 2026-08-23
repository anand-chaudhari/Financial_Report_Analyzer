from datetime import datetime
from typing import List, Optional
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


class ChatQueryRequest(BaseModel):
    report_id: str
    question: str = Field(..., min_length=2, max_length=1000)
    top_k: Optional[int] = 4


class ChatQueryResponse(BaseModel):
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    is_grounded: bool = True
    source_found: bool = True


class ChatHistoryResponse(BaseModel):
    report_id: str
    messages: List[ChatMessageItem] = Field(default_factory=list)
