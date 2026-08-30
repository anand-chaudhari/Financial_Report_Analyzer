from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from ..api.deps import get_current_user
from ..services.financial_service import FinancialService
from ..schemas.financial_schema import (
    FinancialSummaryResponse,
    FinancialChartDataResponse,
    FinancialOverviewResponse,
    RiskAnalysisResponse,
)
from ..schemas.common_schema import ApiResponse

router = APIRouter(prefix="/financials", tags=["Financial Analytics"])
financial_service = FinancialService()


@router.get("/{report_id}/summary", response_model=ApiResponse[FinancialSummaryResponse])
async def get_financial_summary(
    report_id: str,
    refresh: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Generates and returns an executive financial summary and key highlights."""
    user_id = current_user["uid"]
    summary = financial_service.generate_summary(report_id=report_id, user_id=user_id, force_refresh=refresh)
    return ApiResponse(
        success=True,
        message="Financial summary generated successfully.",
        data=summary,
    )


@router.get("/{report_id}/charts", response_model=ApiResponse[FinancialChartDataResponse])
async def get_financial_charts(
    report_id: str,
    refresh: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Extracts and returns structured time-series metrics formatted for Recharts."""
    user_id = current_user["uid"]
    chart_data = financial_service.extract_chart_data(report_id=report_id, user_id=user_id, force_refresh=refresh)
    return ApiResponse(
        success=True,
        message="Financial chart metrics extracted successfully.",
        data=chart_data,
    )


@router.get("/{report_id}/overview", response_model=ApiResponse[FinancialOverviewResponse])
async def get_financial_overview(
    report_id: str,
    refresh: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Feature 2: Extracts automatic grounded Financial Overview comparing FY2025 vs FY2026.
    Extracts only numbers actually available in the report. Missing values default to 'Not available in the report'.
    """
    user_id = current_user["uid"]
    overview = financial_service.get_financial_overview(report_id=report_id, user_id=user_id, force_refresh=refresh)
    return ApiResponse(
        success=True,
        message="Grounded financial overview generated successfully.",
        data=overview,
    )


@router.get("/{report_id}/risks", response_model=ApiResponse[RiskAnalysisResponse])
async def get_financial_risks(
    report_id: str,
    refresh: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Feature 6: Financial Risk & Red Flag Analyzer.
    Extracts factual risks explicitly disclosed or strongly supported by the report.
    Clearly separates 'Reported Risk' from 'Financial Indicator/Observation'.
    """
    user_id = current_user["uid"]
    risks = financial_service.analyze_financial_risks(report_id=report_id, user_id=user_id, force_refresh=refresh)
    return ApiResponse(
        success=True,
        message="Financial risk analysis completed successfully.",
        data=risks,
    )
