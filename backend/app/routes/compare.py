"""
FinSight AI - Comparison Router.
Provides endpoints for multi-document financial comparisons and variance analytics.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ..api.deps import get_current_user
from ..services.comparison_service import ComparisonService, get_comparison_service
from ..services.document_service import DocumentService

router = APIRouter(prefix="/compare", tags=["Comparison"])
doc_service = DocumentService()


class CompareRequest(BaseModel):
    document_a_id: str
    document_b_id: str
    user_id: Optional[str] = None
    focus_metric: Optional[str] = None
    force_refresh: Optional[bool] = False


@router.post("")
def compare_filings(
    req: CompareRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    comp_service: ComparisonService = Depends(get_comparison_service),
) -> Dict[str, Any]:
    """
    Executes side-by-side financial comparison between two documents.
    Enforces authentication and document ownership verification.
    """
    if not req.document_a_id or not req.document_b_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Both document_a_id and document_b_id are required.")

    user_id = current_user["uid"]

    # Verify user ownership of both documents
    doc_a = doc_service.get_document(req.document_a_id, user_id=user_id)
    doc_b = doc_service.get_document(req.document_b_id, user_id=user_id)

    if not doc_a:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document A '{req.document_a_id}' not found or access denied."
        )

    if not doc_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document B '{req.document_b_id}' not found or access denied."
        )

    try:
        result = comp_service.compare_documents(
            doc_a_id=req.document_a_id,
            doc_b_id=req.document_b_id,
            user_id=user_id,
            focus_metric=req.focus_metric,
            force_refresh=bool(req.force_refresh),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Comparison failed: {str(e)}")
