from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class DocumentModel:
    """Domain model representing a stored financial document in Firestore."""
    documentId: str
    userId: str
    fileName: str
    pageCount: int = 0
    status: str = "uploaded"  # uploaded, processing, completed, failed
    currentStage: str = "Ready"  # Uploading, Extracting text, Extracting tables, OCR (only when required), Creating chunks, Generating embeddings, Indexing, Ready, Failed
    stageMessage: Optional[str] = None
    progressPercent: int = 100
    storageUrl: str = ""
    companyName: Optional[str] = None
    financialYear: Optional[str] = None
    fileSize: int = 0
    uploadedAt: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    processedAt: Optional[str] = None
    errorMessage: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "documentId": self.documentId,
            "userId": self.userId,
            "fileName": self.fileName,
            "companyName": self.companyName,
            "financialYear": self.financialYear,
            "pageCount": self.pageCount,
            "status": self.status,
            "currentStage": self.currentStage,
            "stageMessage": self.stageMessage,
            "progressPercent": self.progressPercent,
            "storageUrl": self.storageUrl,
            "fileSize": self.fileSize,
            "uploadedAt": self.uploadedAt,
            "processedAt": self.processedAt,
            "errorMessage": self.errorMessage,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentModel":
        return cls(
            documentId=data.get("documentId", ""),
            userId=data.get("userId", ""),
            fileName=data.get("fileName", ""),
            pageCount=data.get("pageCount", 0),
            status=data.get("status", "uploaded"),
            currentStage=data.get("currentStage", "Ready"),
            stageMessage=data.get("stageMessage"),
            progressPercent=data.get("progressPercent", 100),
            storageUrl=data.get("storageUrl", ""),
            companyName=data.get("companyName"),
            financialYear=data.get("financialYear"),
            fileSize=data.get("fileSize", 0),
            uploadedAt=data.get("uploadedAt", datetime.utcnow().isoformat()),
            processedAt=data.get("processedAt"),
            errorMessage=data.get("errorMessage"),
            metadata=data.get("metadata", {}),
        )
