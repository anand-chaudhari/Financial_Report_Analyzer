from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SourceMetadata(BaseModel):
    page_number: int
    section: str = "General"
    document_name: str = "document.pdf"
    snippet: Optional[str] = ""
    similarity_score: Optional[float] = None


class MessageModelSchema(BaseModel):
    messageId: str
    conversationId: str
    userId: str
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    sources: List[SourceMetadata] = Field(default_factory=list)
    createdAt: str


class ConversationModelSchema(BaseModel):
    conversationId: str
    userId: str
    documentId: str
    title: str
    createdAt: str
    updatedAt: str
    messages: List[MessageModelSchema] = Field(default_factory=list)


class ConversationCreateRequest(BaseModel):
    documentId: str
    title: Optional[str] = "New Financial Analysis"


class ConversationUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class ConversationListResponse(BaseModel):
    success: bool = True
    data: List[ConversationModelSchema] = Field(default_factory=list)
    total: int = 0
