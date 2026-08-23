from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReportBase(BaseModel):
    filename: str
    file_size: int
    total_pages: Optional[int] = 0
    storage_url: Optional[str] = ""


class ReportUploadResponse(BaseModel):
    report_id: str
    filename: str
    status: str = "processing"
    message: str = "Report uploaded and processing queued."


class ReportListItem(BaseModel):
    id: str
    filename: str
    file_size: int
    total_pages: int
    status: str
    uploaded_at: datetime
    company_name: Optional[str] = None
    fiscal_period: Optional[str] = None


class ReportDetailResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    file_size: int
    total_pages: int
    status: str
    uploaded_at: datetime
    storage_url: Optional[str] = ""
    executive_summary: Optional[str] = None
    company_name: Optional[str] = None
    fiscal_period: Optional[str] = None
    error_message: Optional[str] = None


class ReportStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(uploaded|processing|ready|failed)$")
    total_pages: Optional[int] = None
    error_message: Optional[str] = None
