import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from ..models.report_model import ReportModel
from ..document_processing.processor import DocumentProcessor
from ..vectorstore.chroma_client import ChromaVectorService
from ..firebase.firestore import get_firestore_client
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# In-memory storage fallback for local development without active Firebase
_in_memory_reports: Dict[str, ReportModel] = {}


class ReportService:
    """Service handling multi-format report ingestion, extraction, indexing, and lifecycle."""

    def __init__(self):
        self.vector_service = ChromaVectorService()
        self.firestore_db = get_firestore_client()
        self.processor = DocumentProcessor()

    def process_and_index_document(
        self,
        file_bytes: bytes,
        filename: str,
        user_id: str,
        report_id: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> ReportModel:
        """Full pipeline: Multi-format bytes -> Normalized Document -> Chunks -> ChromaDB."""
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
            # 2. Extract and chunk using universal DocumentProcessor
            proc_result = self.processor.process_document(
                file_source=file_bytes,
                document_id=rep_id,
                user_id=user_id,
                file_name=filename,
                mime_type=mime_type,
            )
            report.total_pages = proc_result.total_pages
            report.company_name = proc_result.company_name
            report.fiscal_period = proc_result.financial_year

            # 3. Store embeddings in ChromaDB
            self.vector_service.upsert_chunks(proc_result.chunks)

            # 4. Mark as ready
            report.status = "ready"
            self._save_report(report)
            logger.info(f"Report '{filename}' (ID: {rep_id}) processed and indexed successfully ({proc_result.total_pages} units, {len(proc_result.chunks)} chunks).")
            return report

        except Exception as e:
            logger.error(f"Failed processing report {rep_id}: {str(e)}")
            report.status = "failed"
            report.error_message = str(e)
            self._save_report(report)
            raise e

    def process_and_index_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        user_id: str,
        report_id: Optional[str] = None
    ) -> ReportModel:
        """Backward compatible PDF processing method."""
        return self.process_and_index_document(
            file_bytes=file_bytes,
            filename=filename,
            user_id=user_id,
            report_id=report_id,
            mime_type="application/pdf"
        )

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
        """Lists all reports for a user."""
        reports: List[ReportModel] = []
        if self.firestore_db:
            try:
                docs = (
                    self.firestore_db.collection("reports")
                    .where("user_id", "==", user_id)
                    .stream()
                )
                for doc in docs:
                    reports.append(ReportModel(**doc.to_dict()))
            except Exception as e:
                logger.error(f"Firestore list_reports error: {str(e)}")

        for rep in _in_memory_reports.values():
            if rep.user_id == user_id and not any(r.id == rep.id for r in reports):
                reports.append(rep)

        return sorted(reports, key=lambda x: x.uploaded_at, reverse=True)

    def delete_report(self, report_id: str, user_id: str) -> bool:
        """Deletes a report, its Firestore metadata, and its vector embeddings."""
        report = self.get_report(report_id, user_id)
        if not report:
            return False

        if self.firestore_db:
            try:
                self.firestore_db.collection("reports").document(report_id).delete()
            except Exception as e:
                logger.error(f"Firestore delete_report error: {str(e)}")

        if report_id in _in_memory_reports:
            del _in_memory_reports[report_id]

        self.vector_service.delete_report_embeddings(report_id)
        return True

    def _save_report(self, report: ReportModel) -> None:
        """Helper to save report to Firestore and in-memory cache."""
        _in_memory_reports[report.id] = report
        if self.firestore_db:
            try:
                self.firestore_db.collection("reports").document(report.id).set(report.to_dict())
            except Exception as e:
                logger.error(f"Firestore save error: {str(e)}")
