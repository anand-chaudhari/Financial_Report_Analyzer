from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, BackgroundTasks
from ..api.deps import get_current_user
from ..services.report_service import ReportService
from ..schemas.report_schema import (
    ReportUploadResponse,
    ReportListItem,
    ReportDetailResponse,
)
from ..schemas.common_schema import ApiResponse
from ..utils.helpers import sanitize_filename
from ..config import get_settings

router = APIRouter(prefix="/reports", tags=["Reports"])
report_service = ReportService()


@router.post("/upload", response_model=ApiResponse[ReportUploadResponse])
async def upload_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Uploads a PDF financial report and triggers background parsing and vector indexing."""
    settings = get_settings()

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported."
        )

    file_bytes = await file.read()
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    cleaned_filename = sanitize_filename(file.filename)
    user_id = current_user["uid"]

    # Process PDF and index into ChromaDB
    report = report_service.process_and_index_pdf(
        file_bytes=file_bytes,
        filename=cleaned_filename,
        user_id=user_id
    )

    return ApiResponse(
        success=True,
        message="Financial report uploaded and indexed successfully.",
        data=ReportUploadResponse(
            report_id=report.id,
            filename=report.filename,
            status=report.status,
            message="Ready for AI Q&A and Financial Analysis."
        )
    )


@router.get("", response_model=ApiResponse[List[ReportListItem]])
async def list_reports(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves all reports uploaded by the authenticated user."""
    user_id = current_user["uid"]
    reports = report_service.list_reports(user_id=user_id)
    items = [
        ReportListItem(
            id=r.id,
            filename=r.filename,
            file_size=r.file_size,
            total_pages=r.total_pages,
            status=r.status,
            uploaded_at=r.uploaded_at,
            company_name=r.company_name,
            fiscal_period=r.fiscal_period
        )
        for r in reports
    ]
    return ApiResponse(success=True, data=items)


@router.get("/{report_id}", response_model=ApiResponse[ReportDetailResponse])
async def get_report_detail(
    report_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Fetches full metadata and status for a specific report."""
    user_id = current_user["uid"]
    report = report_service.get_report(report_id=report_id, user_id=user_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' not found."
        )

    return ApiResponse(
        success=True,
        data=ReportDetailResponse(
            id=report.id,
            user_id=report.user_id,
            filename=report.filename,
            file_size=report.file_size,
            total_pages=report.total_pages,
            status=report.status,
            uploaded_at=report.uploaded_at,
            storage_url=report.storage_url,
            executive_summary=report.executive_summary,
            company_name=report.company_name,
            fiscal_period=report.fiscal_period,
            error_message=report.error_message
        )
    )


@router.delete("/{report_id}", response_model=ApiResponse[Dict[str, Any]])
async def delete_report(
    report_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Deletes a report, vector chunks, and associated metadata."""
    user_id = current_user["uid"]
    success = report_service.delete_report(report_id=report_id, user_id=user_id)
    return ApiResponse(
        success=success,
        message=f"Report '{report_id}' and all associated vector embeddings deleted successfully."
    )
