import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from ..models.report_model import ReportModel
from ..document_processing.pdf_extractor import extract_text_from_pdf
from ..document_processing.chunker import chunk_document_pages
from ..vectorstore.chroma_client import ChromaVectorService
from ..firebase.firestore import get_firestore_client
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# In-memory storage fallback for local development without active Firebase
_in_memory_reports: Dict[str, ReportModel] = {}


class ReportService:
    """Service handling report ingestion, extraction, indexing, and lifecycle."""

    def __init__(self):
        self.vector_service = ChromaVectorService()
        self.firestore_db = get_firestore_client()

    def process_and_index_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        user_id: str,
        report_id: Optional[str] = None
    ) -> ReportModel:
        """Full pipeline: PDF bytes -> PyMuPDF pages -> Clean/Chunk -> ChromaDB."""
        rep_id = report_id or str(uuid.uuid4())
        
        # 1. Initialize record
        report = ReportModel(
            id=rep_id,
            user_id=user_id,
            filename=filename,
            file_size=len(file_bytes),
            storage_url="",
            status="processing",
            uploaded_at=datetime.utcnow()
        )
        self._save_report(report)

        try:
            # 2. Extract pages with PyMuPDF
            pages = extract_text_from_pdf(file_bytes)
            report.total_pages = len(pages)

            # 3. Semantic Chunking with Page Tracking
            chunks = chunk_document_pages(
                pages=pages,
                report_id=rep_id,
                user_id=user_id
            )

            # 4. Store embeddings in ChromaDB
            self.vector_service.upsert_chunks(chunks)

            # 5. Mark as ready
            report.status = "ready"
            self._save_report(report)
            logger.info(f"Report '{filename}' (ID: {rep_id}) processed and indexed successfully.")
            return report

        except Exception as e:
            logger.error(f"Failed processing PDF report {rep_id}: {str(e)}")
            report.status = "failed"
            report.error_message = str(e)
            self._save_report(report)
            raise e

    def get_report(self, report_id: str, user_id: str) -> Optional[ReportModel]:
        """Retrieves a single report by ID."""
        if self.firestore_db:
            try:
                doc = self.firestore_db.collection("reports").document(report_id).get()
                if doc.exists:
                    data = doc.to_dict()
                    if data.get("user_id") == user_id:
                        return ReportModel(**data)
            except Exception as e:
                logger.error(f"Firestore get_report error: {str(e)}")
        
        report = _in_memory_reports.get(report_id)
        if report and report.user_id == user_id:
            return report
        return None

    def list_reports(self, user_id: str) -> List[ReportModel]:
        """Lists all reports for a specific user."""
        if self.firestore_db:
            try:
                docs = (
                    self.firestore_db.collection("reports")
                    .where("user_id", "==", user_id)
                    .stream()
                )
                return [ReportModel(**doc.to_dict()) for doc in docs]
            except Exception as e:
                logger.error(f"Firestore list_reports error: {str(e)}")

        return [r for r in _in_memory_reports.values() if r.user_id == user_id]

    def delete_report(self, report_id: str, user_id: str) -> bool:
        """Deletes a report, its vector chunks, Firestore records, and invalidates AI cache."""
        from .cache_service import get_ai_cache_service
        get_ai_cache_service().invalidate_document_cache(document_id=report_id, user_id=user_id)

        # 1. Delete ChromaDB vector embeddings
        self.vector_service.delete_report_chunks(report_id)

        # 2. Delete Firestore record
        if self.firestore_db:
            try:
                self.firestore_db.collection("reports").document(report_id).delete()
            except Exception as e:
                logger.error(f"Firestore delete error: {str(e)}")

        # 3. Delete from in-memory fallback
        if report_id in _in_memory_reports:
            del _in_memory_reports[report_id]

        return True

    def _save_report(self, report: ReportModel) -> None:
        """Persists report model to Firestore and in-memory cache."""
        _in_memory_reports[report.id] = report
        if self.firestore_db:
            try:
                self.firestore_db.collection("reports").document(report.id).set(
                    report.to_dict()
                )
            except Exception as e:
                logger.error(f"Firestore save error: {str(e)}")
