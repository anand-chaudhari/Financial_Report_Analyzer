from typing import Dict, Any, List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from ..api.deps import get_current_user
from ..services.document_service import DocumentService
from ..services.summary_service import SummaryService
from ..services.financial_service import FinancialService
from ..schemas.document_schema import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentMetadata,
)
from ..schemas.summary_schema import DocumentSummaryResponse
from ..schemas.financial_schema import FinancialOverviewResponse, RiskAnalysisResponse
from ..utils.helpers import sanitize_filename
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])
document_service = DocumentService()
summary_service = SummaryService()
financial_service = FinancialService()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Secure endpoint to upload a financial report in PDF format:
    1. Authenticates user via Firebase Bearer token
    2. Validates PDF format, magic bytes, and file size limits
    3. Generates unique document ID
    4. Stores file and creates Firestore metadata record
    5. Returns document metadata with processing state
    """
    settings = get_settings()

    # 1. Filename & Extension Validation
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF documents (.pdf) are supported."
        )

    # 2. Read File Bytes
    try:
        file_bytes = await file.read()
    except Exception as e:
        logger.error(f"Error reading uploaded file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file."
        )

    # 3. Empty File Validation
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    # 4. Maximum File Size Validation
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size ({len(file_bytes) / (1024*1024):.2f}MB) exceeds the maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    # 5. Magic Byte Header Check (%PDF-)
    if not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupted or invalid PDF header. Please upload a valid PDF document."
        )

    # 6. Derive Authenticated User ID (Never trust client-supplied user ID)
    user_id = current_user.get("uid")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user identity could not be verified."
        )

    cleaned_filename = sanitize_filename(file.filename)
    logger.info(f"Processing upload for user '{user_id}': '{cleaned_filename}' ({len(file_bytes)} bytes)")

    # 7. Process & Store Document (Extract metadata, save to Firestore)
    try:
        doc = document_service.process_and_save_upload(
            file_bytes=file_bytes,
            filename=cleaned_filename,
            user_id=user_id
        )

        metadata = DocumentMetadata(
            documentId=doc.documentId,
            userId=doc.userId,
            fileName=doc.fileName,
            companyName=doc.companyName,
            financialYear=doc.financialYear,
            pageCount=doc.pageCount,
            status=doc.status,
            storageUrl=doc.storageUrl,
            uploadedAt=doc.uploadedAt,
            processedAt=doc.processedAt,
            fileSize=doc.fileSize,
            errorMessage=doc.errorMessage,
        )

        return DocumentUploadResponse(
            success=True,
            message="Document uploaded and processed successfully.",
            data=metadata
        )

    except Exception as e:
        logger.error(f"Error processing document upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and store document: {str(e)}"
        )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Lists all financial documents uploaded by the authenticated user."""
    user_id = current_user["uid"]
    docs = document_service.list_user_documents(user_id=user_id)

    items = [
        DocumentMetadata(
            documentId=d.documentId,
            userId=d.userId,
            fileName=d.fileName,
            companyName=d.companyName,
            financialYear=d.financialYear,
            pageCount=d.pageCount,
            status=d.status,
            storageUrl=d.storageUrl,
            uploadedAt=d.uploadedAt,
            processedAt=d.processedAt,
            fileSize=d.fileSize,
            errorMessage=d.errorMessage,
        )
        for d in docs
    ]

    return DocumentListResponse(
        success=True,
        data=items,
        total=len(items)
    )


@router.get("/{document_id}", response_model=DocumentUploadResponse)
async def get_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves metadata and processing status for a single document."""
    user_id = current_user["uid"]
    doc = document_service.get_document(document_id=document_id, user_id=user_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    metadata = DocumentMetadata(
        documentId=doc.documentId,
        userId=doc.userId,
        fileName=doc.fileName,
        companyName=doc.companyName,
        financialYear=doc.financialYear,
        pageCount=doc.pageCount,
        status=doc.status,
        storageUrl=doc.storageUrl,
        uploadedAt=doc.uploadedAt,
        processedAt=doc.processedAt,
        fileSize=doc.fileSize,
        errorMessage=doc.errorMessage,
    )

    return DocumentUploadResponse(
        success=True,
        message="Document retrieved successfully.",
        data=metadata
    )


@router.post("/{document_id}/summary", response_model=DocumentSummaryResponse)
async def generate_document_summary(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generates a grounded 11-section financial summary for the specified document:
    1. Executive Summary
    2. Key Financial Highlights
    3. Revenue
    4. Profit/Loss
    5. Major Expenses
    6. Assets
    7. Liabilities
    8. Cash Flow
    9. Business Risks
    10. Management Discussion
    11. Future Plans
    STRICT GROUNDING: Sections without supporting text are marked 'Not available in the uploaded report.'
    """
    user_id = current_user["uid"]
    try:
        summary = summary_service.generate_document_summary(document_id=document_id, user_id=user_id)
        return summary
    except Exception as e:
        logger.error(f"Error generating document summary for '{document_id}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate document summary: {str(e)}"
        )


@router.get("/{document_id}/overview", response_model=FinancialOverviewResponse)
async def get_document_financial_overview(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Feature 2: Automatic Financial Report Overview comparing FY2025 vs FY2026.
    Extracts only metrics reported in the PDF filing.
    """
    user_id = current_user["uid"]
    try:
        return financial_service.get_financial_overview(report_id=document_id, user_id=user_id)
    except Exception as e:
        logger.error(f"Error generating financial overview for '{document_id}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate financial overview: {str(e)}"
        )


@router.get("/{document_id}/risks", response_model=RiskAnalysisResponse)
async def get_document_financial_risks(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Feature 6: Financial Risk & Red Flag Analyzer.
    Extracts factual risks explicitly disclosed or strongly supported by the report.
    Clearly separates 'Reported Risk' from 'Financial Indicator/Observation'.
    """
    user_id = current_user["uid"]
    try:
        return financial_service.analyze_financial_risks(report_id=document_id, user_id=user_id)
    except Exception as e:
        logger.error(f"Error analyzing risks for '{document_id}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze financial risks: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Deletes a document record and its associated storage."""
    user_id = current_user["uid"]
    success = document_service.delete_document(document_id=document_id, user_id=user_id)
    return {
        "success": success,
        "message": f"Document '{document_id}' deleted successfully."
    }
