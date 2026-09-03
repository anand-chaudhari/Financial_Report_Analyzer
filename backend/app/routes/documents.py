import os
import uuid
import asyncio
from typing import Dict, Any, List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from ..api.deps import get_current_user
from ..api.rate_limiter import check_ai_rate_limit, check_upload_rate_limit
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


@router.post("/upload", response_model=DocumentUploadResponse, dependencies=[Depends(check_upload_rate_limit)])
async def upload_document(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Secure streaming endpoint to upload financial reports up to 200MB:
    1. Authenticates user via Firebase Bearer token
    2. Streams file to disk in 1MB chunks to keep localhost RAM flat
    3. Validates format and magic bytes via FileTypeDetector
    4. Executes incremental processing pipeline (Analyzing -> Extracting -> OCR -> Chunking -> Embedding -> Indexing -> Ready)
    5. Cleans up temporary upload file safely
    """
    user_id = current_user.get("uid")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user identity could not be verified."
        )

    cleaned_filename = sanitize_filename(file.filename or "report.pdf")
    temp_dir = os.path.join(os.getcwd(), "uploads", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f"temp_{uuid.uuid4().hex}_{cleaned_filename}")

    # 1. Stream file chunks to disk (Zero memory overhead for 200MB PDFs)
    try:
        total_bytes = 0
        with open(temp_file_path, "wb") as f_out:
            while True:
                chunk = await file.read(1024 * 1024)  # 1 MB stream
                if not chunk:
                    break
                f_out.write(chunk)
                total_bytes += len(chunk)
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        logger.error(f"Error streaming uploaded file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to receive uploaded file stream."
        )

    # 2. File Format and Size Validation via FileTypeDetector
    from ..document_processing.file_detector import FileTypeDetector, UnsupportedFileFormatException
    try:
        detected_fmt, file_size = FileTypeDetector.validate_file(
            file_bytes_or_path=temp_file_path,
            filename=cleaned_filename,
            mime_type=file.content_type
        )
    except UnsupportedFileFormatException as uf_err:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(uf_err)
        )
    except Exception as val_err:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file: {str(val_err)}"
        )

    logger.info(f"Processing streamed upload for user '{user_id}': '{cleaned_filename}' ({file_size / (1024*1024):.2f} MB)")

    # 3. Process & Store Document (Extract metadata, save to Firestore asynchronously without blocking event loop)
    try:
        doc = await asyncio.to_thread(
            document_service.process_and_save_upload,
            file_path=temp_file_path,
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
            currentStage=doc.currentStage,
            stageMessage=doc.stageMessage,
            progressPercent=doc.progressPercent,
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
            detail=f"Error processing document: {str(e)}"
        )
    finally:
        # Temporary file cleanup
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass


@router.post("/{document_id}/cancel")
async def cancel_document_processing(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Cancels an in-progress document processing pipeline."""
    cancelled = document_service.cancel_processing(document_id)
    return {
        "success": True,
        "cancelled": cancelled,
        "message": f"Cancellation request registered for document '{document_id}'."
    }


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
            currentStage=d.currentStage,
            stageMessage=d.stageMessage,
            progressPercent=d.progressPercent,
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


@router.get("/{document_id}/status", response_model=DocumentUploadResponse)
async def get_document_status(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves live processing stage and progress for a document."""
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
        currentStage=doc.currentStage,
        stageMessage=doc.stageMessage,
        progressPercent=doc.progressPercent,
        storageUrl=doc.storageUrl,
        uploadedAt=doc.uploadedAt,
        processedAt=doc.processedAt,
        fileSize=doc.fileSize,
        errorMessage=doc.errorMessage,
    )

    return DocumentUploadResponse(
        success=True,
        message=f"Document status: {doc.status} ({doc.currentStage})",
        data=metadata
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
        currentStage=doc.currentStage,
        stageMessage=doc.stageMessage,
        progressPercent=doc.progressPercent,
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
    refresh: bool = False,
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
        summary = await asyncio.to_thread(
            summary_service.generate_document_summary,
            document_id=document_id,
            user_id=user_id,
            force_refresh=refresh,
        )
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
    refresh: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Feature 2: Automatic Financial Report Overview comparing FY2025 vs FY2026.
    Extracts only metrics reported in the filing with persistent result caching.
    """
    user_id = current_user["uid"]
    try:
        return await asyncio.to_thread(
            financial_service.get_financial_overview,
            report_id=document_id,
            user_id=user_id,
            force_refresh=refresh,
        )
    except Exception as e:
        logger.error(f"Error generating financial overview for '{document_id}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate financial overview: {str(e)}"
        )


@router.get("/{document_id}/risks", response_model=RiskAnalysisResponse)
async def get_document_financial_risks(
    document_id: str,
    refresh: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Feature 6: Financial Risk & Red Flag Analyzer.
    Extracts factual risks explicitly disclosed with persistent result caching.
    """
    user_id = current_user["uid"]
    try:
        return await asyncio.to_thread(
            financial_service.analyze_financial_risks,
            report_id=document_id,
            user_id=user_id,
            force_refresh=refresh,
        )
    except Exception as e:
        logger.error(f"Error analyzing risks for '{document_id}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze financial risks: {str(e)}"
        )


from fastapi.responses import FileResponse

@router.get("/{document_id}/file")
async def download_document_file(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Authenticated endpoint to stream/download uploaded PDF filing.
    Enforces strict user ownership verification.
    """
    user_id = current_user["uid"]
    doc = document_service.get_document(document_id=document_id, user_id=user_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found or access denied."
        )

    file_path = document_service.get_document_file_path(document_id=document_id, user_id=user_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document PDF file could not be found on disk."
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=doc.fileName or f"{document_id}.pdf"
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
