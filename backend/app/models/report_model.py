from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class ReportModel:
    """Domain model representing an uploaded financial report."""
    id: str
    user_id: str
    filename: str
    file_size: int
    storage_url: str
    status: str = "uploaded"  # uploaded, processing, ready, failed
    total_pages: int = 0
    uploaded_at: datetime = field(default_factory=datetime.utcnow)
    company_name: Optional[str] = None
    fiscal_period: Optional[str] = None
    executive_summary: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "storage_url": self.storage_url,
            "status": self.status,
            "total_pages": self.total_pages,
            "uploaded_at": self.uploaded_at.isoformat() if isinstance(self.uploaded_at, datetime) else self.uploaded_at,
            "company_name": self.company_name,
            "fiscal_period": self.fiscal_period,
            "executive_summary": self.executive_summary,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }
