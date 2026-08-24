from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from ..api.deps import get_current_user
from ..services.chat_service import ChatService
from ..schemas.chat_schema import (
    ChatRequest,
    ChatResponse,
    ChatQueryRequest,
    ChatQueryResponse,
    ChatMessageItem,
    ChatHistoryResponse,
)
from ..schemas.common_schema import ApiResponse

router = APIRouter(prefix="", tags=["Chat & RAG Q&A"])
chat_service = ChatService()


@router.post("/chat", response_model=ChatResponse)
async def chat_rag(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    POST /api/chat
    Request: document_id, question, conversation_history
    Response: answer, sources, pages, sections, retrieved_chunks
    """
    user_id = current_user["uid"]
    doc_id = request.target_document_id

    response = chat_service.process_query(
        document_id=doc_id,
        question=request.question,
        user_id=user_id,
        conversation_history=request.conversation_history,
        top_k=request.top_k or 8,
    )
    return response


@router.post("/chat/query", response_model=ApiResponse[ChatQueryResponse])
async def query_report(
    request: ChatQueryRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Executes a grounded RAG query wrapped in standard ApiResponse envelope."""
    user_id = current_user["uid"]
    doc_id = request.target_document_id

    response = chat_service.process_query(
        document_id=doc_id,
        question=request.question,
        user_id=user_id,
        conversation_history=request.conversation_history,
        top_k=request.top_k or 8,
    )
    return ApiResponse(
        success=True,
        message="Answer generated with Groq LLM grounded vector citations.",
        data=response,
    )


@router.get("/chat/{report_id}/history", response_model=ApiResponse[ChatHistoryResponse])
async def get_chat_history(
    report_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Fetches full conversation history for a report."""
    user_id = current_user["uid"]
    history = chat_service.get_history(report_id=report_id, user_id=user_id)
    return ApiResponse(
        success=True,
        data=ChatHistoryResponse(report_id=report_id, messages=history),
    )


@router.delete("/chat/{report_id}/history", response_model=ApiResponse[Dict[str, Any]])
async def clear_chat_history(
    report_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Clears conversation history for a report."""
    user_id = current_user["uid"]
    chat_service.clear_history(report_id=report_id, user_id=user_id)
    return ApiResponse(
        success=True,
        message=f"Chat history for report '{report_id}' cleared successfully.",
    )
