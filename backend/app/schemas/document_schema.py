from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    documentId: str = Field(..., description="Unique identifier for the document")
    userId: str = Field(..., description="Authenticated Firebase User ID")
    fileName: str = Field(..., description="Original name of the uploaded PDF file")
    companyName: Optional[str] = Field(None, description="Extracted company name")
    financialYear: Optional[str] = Field(None, description="Extracted fiscal year (e.g., FY2024)")
    pageCount: int = Field(0, description="Total number of pages in the PDF")
    status: str = Field("uploaded", description="Processing state: uploaded, processing, completed, failed")
    storageUrl: str = Field("", description="URL or path where the file is stored")
    uploadedAt: str = Field(..., description="ISO 8601 timestamp of upload")
    processedAt: Optional[str] = Field(None, description="ISO 8601 timestamp when processing completed")
    fileSize: int = Field(0, description="Size of the file in bytes")
    errorMessage: Optional[str] = Field(None, description="Error message if processing failed")


class DocumentUploadResponse(BaseModel):
    success: bool = True
    message: str = "Document uploaded successfully."
    data: DocumentMetadata


class DocumentListResponse(BaseModel):
    success: bool = True
    data: List[DocumentMetadata]
    total: int = 0
