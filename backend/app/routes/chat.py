import asyncio
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from ..api.deps import get_current_user
from ..api.rate_limiter import check_ai_rate_limit
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
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="", tags=["Chat & RAG Q&A"])
chat_service = ChatService()


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(check_ai_rate_limit)])
async def chat_rag(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    POST /api/chat
    Request: document_id, question, conversation_history, use_web_search
    Response: answer, sources, pages, sections, retrieved_chunks, web_sources, market_data
    """
    user_id = current_user["uid"]
    doc_id = request.target_document_id

    try:
        response = await asyncio.to_thread(
            chat_service.process_query,
            document_id=doc_id,
            question=request.question,
            user_id=user_id,
            conversation_id=request.target_conversation_id,
            conversation_history=request.conversation_history,
            top_k=request.top_k or 8,
            use_web_search=request.target_web_search,
            search_mode=request.target_search_mode,
        )
        return response
    except Exception as e:
        logger.error(f"Chat query error for doc '{doc_id}': {str(e)}", exc_info=True)
        return ChatResponse(
            conversationId=request.target_conversation_id or f"conv_{doc_id or 'general'}",
            messageId=f"msg_fb_{doc_id or 'gen'}",
            answer="I am analyzing your financial statement. Please try asking a specific question such as 'What was the revenue?' or 'What is the net profit?'.",
            sources=[],
            pages=[],
            sections=[],
            retrieved_chunks=[],
            citations=[],
            is_grounded=True,
            source_found=False
        )


@router.post("/chat/stream", dependencies=[Depends(check_ai_rate_limit)])
async def chat_rag_stream(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    POST /api/chat/stream
    Server-Sent Events (SSE) streaming endpoint returning real-time generated tokens.
    """
    import json
    import queue
    import threading
    from fastapi.responses import StreamingResponse

    user_id = current_user["uid"]
    doc_id = request.target_document_id

    async def event_generator():
        try:
            q = queue.Queue()
            sentinel = object()

            def run_gen():
                try:
                    for event in chat_service.process_query_stream(
                        document_id=doc_id,
                        question=request.question,
                        user_id=user_id,
                        conversation_id=request.target_conversation_id,
                        conversation_history=request.conversation_history,
                        top_k=request.top_k or 8,
                        use_web_search=request.target_web_search,
                        search_mode=request.target_search_mode,
                    ):
                        q.put(event)
                except Exception as ex:
                    q.put({"type": "error", "error": str(ex)})
                finally:
                    q.put(sentinel)

            t = threading.Thread(target=run_gen, daemon=True)
            t.start()

            while True:
                try:
                    item = q.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.02)
                    continue

                if item is sentinel:
                    break

                yield f"data: {json.dumps(item)}\n\n"
        except Exception as e:
            logger.error(f"Streaming generator error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/chat/query", response_model=ApiResponse[ChatQueryResponse], dependencies=[Depends(check_ai_rate_limit)])
async def query_report(
    request: ChatQueryRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Executes a grounded RAG query wrapped in standard ApiResponse envelope."""
    user_id = current_user["uid"]
    doc_id = request.target_document_id

    response = await asyncio.to_thread(
        chat_service.process_query,
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
