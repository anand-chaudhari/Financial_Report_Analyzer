"""
FinSight AI - Comparison Router.
Provides endpoints for multi-document financial comparisons and variance analytics.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ..services.comparison_service import ComparisonService, get_comparison_service

router = APIRouter(prefix="/compare", tags=["Comparison"])


class CompareRequest(BaseModel):
    document_a_id: str
    document_b_id: str
    user_id: Optional[str] = "dev_user_123"
    focus_metric: Optional[str] = None


@router.post("")
def compare_filings(
    req: CompareRequest,
    comp_service: ComparisonService = Depends(get_comparison_service),
) -> Dict[str, Any]:
    """
    Executes side-by-side financial comparison between two documents.
    """
    if not req.document_a_id or not req.document_b_id:
        raise HTTPException(status_code=400, detail="Both document_a_id and document_b_id are required.")

    try:
        result = comp_service.compare_documents(
            doc_a_id=req.document_a_id,
            doc_b_id=req.document_b_id,
            user_id=req.user_id or "dev_user_123",
            focus_metric=req.focus_metric,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")
