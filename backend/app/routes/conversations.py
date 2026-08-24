from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from ..api.deps import get_current_user
from ..services.conversation_service import ConversationService
from ..schemas.conversation_schema import (
    ConversationModelSchema,
    ConversationCreateRequest,
    ConversationUpdateRequest,
    ConversationListResponse,
    MessageModelSchema,
)
from ..schemas.common_schema import ApiResponse
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations"])
conv_service = ConversationService()


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    document_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Lists all persistent conversations belonging strictly to the authenticated user.
    Never allows one user to read another user's conversations.
    """
    user_id = current_user["uid"]
    convs = conv_service.list_user_conversations(user_id=user_id, document_id=document_id)

    items = []
    for c in convs:
        items.append(
            ConversationModelSchema(
                conversationId=c.conversationId,
                userId=c.userId,
                documentId=c.documentId,
                title=c.title,
                createdAt=c.createdAt,
                updatedAt=c.updatedAt,
                messages=[]
            )
        )

    return ConversationListResponse(
        success=True,
        data=items,
        total=len(items)
    )


@router.post("", response_model=ApiResponse[ConversationModelSchema])
async def create_conversation(
    request: ConversationCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Creates a new conversation thread for the authenticated user.
    """
    user_id = current_user["uid"]
    conv = conv_service.create_conversation(
        user_id=user_id,
        document_id=request.documentId,
        title=request.title
    )

    return ApiResponse(
        success=True,
        message="Conversation thread created successfully.",
        data=ConversationModelSchema(
            conversationId=conv.conversationId,
            userId=conv.userId,
            documentId=conv.documentId,
            title=conv.title,
            createdAt=conv.createdAt,
            updatedAt=conv.updatedAt,
            messages=[]
        )
    )


@router.get("/{conversation_id}", response_model=ApiResponse[ConversationModelSchema])
async def get_conversation(
    conversation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Retrieves a single conversation and its message history.
    Enforces strict user ownership: Throws 403 / 404 if user does not own the conversation.
    """
    user_id = current_user["uid"]
    conv = conv_service.get_conversation(conversation_id=conversation_id, user_id=user_id)

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found or access denied."
        )

    message_schemas = [
        MessageModelSchema(
            messageId=m.messageId,
            conversationId=m.conversationId,
            userId=m.userId,
            role=m.role,
            content=m.content,
            sources=m.sources,
            createdAt=m.createdAt,
        )
        for m in conv.messages
    ]

    return ApiResponse(
        success=True,
        data=ConversationModelSchema(
            conversationId=conv.conversationId,
            userId=conv.userId,
            documentId=conv.documentId,
            title=conv.title,
            createdAt=conv.createdAt,
            updatedAt=conv.updatedAt,
            messages=message_schemas
        )
    )


@router.patch("/{conversation_id}", response_model=ApiResponse[ConversationModelSchema])
async def rename_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Renames a conversation title. Enforces user ownership.
    """
    user_id = current_user["uid"]
    success = conv_service.update_conversation_title(
        conversation_id=conversation_id,
        user_id=user_id,
        title=request.title
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found or access denied."
        )

    conv = conv_service.get_conversation(conversation_id=conversation_id, user_id=user_id)
    return ApiResponse(
        success=True,
        message="Conversation title updated successfully.",
        data=ConversationModelSchema(
            conversationId=conv.conversationId,
            userId=conv.userId,
            documentId=conv.documentId,
            title=conv.title,
            createdAt=conv.createdAt,
            updatedAt=conv.updatedAt,
            messages=[]
        )
    )


@router.delete("/{conversation_id}", response_model=ApiResponse[Dict[str, Any]])
async def delete_conversation(
    conversation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Deletes a conversation and its messages. Enforces user ownership.
    """
    user_id = current_user["uid"]
    success = conv_service.delete_conversation(conversation_id=conversation_id, user_id=user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found or access denied."
        )

    return ApiResponse(
        success=True,
        message=f"Conversation '{conversation_id}' deleted successfully."
    )
