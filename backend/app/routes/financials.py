from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from ..api.deps import get_current_user
from ..services.financial_service import FinancialService
from ..schemas.financial_schema import (
    FinancialSummaryResponse,
    FinancialChartDataResponse,
)
from ..schemas.common_schema import ApiResponse

router = APIRouter(prefix="/financials", tags=["Financial Analytics"])
financial_service = FinancialService()


@router.get("/{report_id}/summary", response_model=ApiResponse[FinancialSummaryResponse])
async def get_financial_summary(
    report_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Generates and returns an executive financial summary and key highlights."""
    user_id = current_user["uid"]
    summary = financial_service.generate_summary(report_id=report_id, user_id=user_id)
    return ApiResponse(
        success=True,
        message="Financial summary generated successfully.",
        data=summary,
    )


@router.get("/{report_id}/charts", response_model=ApiResponse[FinancialChartDataResponse])
async def get_financial_charts(
    report_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Extracts and returns structured time-series metrics formatted for Recharts."""
    user_id = current_user["uid"]
    chart_data = financial_service.extract_chart_data(report_id=report_id, user_id=user_id)
    return ApiResponse(
        success=True,
        message="Financial chart metrics extracted successfully.",
        data=chart_data,
    )
