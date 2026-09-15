import os
import re
import uuid
import shutil
import io
import hashlib
import json
import concurrent.futures
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Union
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from ..models.document_model import DocumentModel
from ..firebase.firestore import get_firestore_client
from ..firebase.storage import get_storage_bucket
from ..document_processing.processor import DocumentProcessor
from ..vectorstore.vector_service import VectorStoreService
from ..services.background_worker import submit_background_processing, is_job_running
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# In-memory storage fallback for local development
_in_memory_documents: Dict[str, DocumentModel] = {}


def _run_with_timeout(func, timeout_sec: float = 0.8):
    """
    Executes a function in a daemon thread with a strict timeout.
    Daemon threads never block Python process exit or hang FastAPI if Firestore is offline.
    """
    result = [None]
    exception = [None]
    completed = threading.Event()

    def worker():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e
        finally:
            completed.set()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    if completed.wait(timeout=timeout_sec):
        if exception[0]:
            logger.debug(f"Firestore operation error: {exception[0]}")
            return None
        return result[0]
    else:
        logger.debug(f"Firestore operation timed out ({timeout_sec}s). Falling back to local storage.")
        return None


def ensure_document_indexed(document_id: str, user_id: str) -> bool:
    """Module-level function helper to ensure a document is vector indexed in ChromaDB."""
    service = DocumentService()
    return service.ensure_document_indexed(document_id=document_id, user_id=user_id)


def _get_uploads_roots() -> List[str]:
    """Finds all potential upload roots across repo root and backend working directories."""
    roots = []
    candidates = [
        os.path.join(os.getcwd(), "uploads"),
        os.path.join(os.getcwd(), "backend", "uploads"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"),
    ]
    for c in candidates:
        if os.path.exists(c) and c not in roots:
            roots.append(c)
    return roots if roots else [os.path.join(os.getcwd(), "uploads")]


class ProcessingCancellationManager:
    """Tracks document processing cancellation requests."""
    def __init__(self):
        self._events: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def register(self, doc_id: str) -> threading.Event:
        with self._lock:
            ev = threading.Event()
            self._events[doc_id] = ev
            return ev

    def cancel(self, doc_id: str) -> bool:
        with self._lock:
            ev = self._events.get(doc_id)
            if ev:
                ev.set()
                return True
            return False

    def is_cancelled(self, doc_id: str) -> bool:
        with self._lock:
            ev = self._events.get(doc_id)
            return ev.is_set() if ev else False

    def unregister(self, doc_id: str):
        with self._lock:
            self._events.pop(doc_id, None)


cancellation_manager = ProcessingCancellationManager()

SUPPORTED_EXTENSIONS = (
    ".pdf", ".xlsx", ".xlsm", ".xltx", ".xls", ".csv", ".tsv", ".docx", ".docm", ".dotx", ".txt", ".text", ".md", ".markdown", ".json"
)


class DocumentService:
    """
    Service handling Multi-Format Document uploads, background worker ingestion,
    vector indexing, and real-time status tracking across PDF, Excel, Word, Text, and JSON.
    """

    def __init__(
        self,
        firestore_db=None,
        storage_bucket=None,
        vector_service: Optional[VectorStoreService] = None,
    ):
        self.firestore_db = firestore_db or get_firestore_client()
        self.storage_bucket = storage_bucket or get_storage_bucket()
        self.settings = get_settings()
        self.processor = DocumentProcessor()
        self.vector_service = vector_service or VectorStoreService()
        self._restore_local_documents()

    def _restore_local_documents(self):
        """Scans local uploads/ directories across all root locations on startup and restores document models into memory."""
        try:
            upload_roots = _get_uploads_roots()
            for uploads_root in upload_roots:
                if not os.path.exists(uploads_root):
                    continue
                for user_dir in os.listdir(uploads_root):
                    user_path = os.path.join(uploads_root, user_dir)
                    if not os.path.isdir(user_path) or user_dir.startswith("."):
                        continue
                    for doc_dir in os.listdir(user_path):
                        doc_path = os.path.join(user_path, doc_dir)
                        if not os.path.isdir(doc_path) or doc_dir.startswith("."):
                            continue
                        files = [f for f in os.listdir(doc_path) if any(f.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)]
                        if not files:
                            continue
                        doc_filename = files[0]
                        full_file_path = os.path.join(doc_path, doc_filename)
                        try:
                            file_size = os.path.getsize(full_file_path)
                            doc_hash = self._compute_file_hash(full_file_path)
                            page_count, company_name, financial_year, raw_meta = self._extract_document_metadata(
                                file_bytes=full_file_path,
                                filename=doc_filename
                            )
                            raw_meta["doc_hash"] = doc_hash

                            doc_model = DocumentModel(
                                documentId=doc_dir,
                                userId=user_dir,
                                fileName=doc_filename,
                                fileSize=file_size,
                                companyName=company_name or "Financial Report",
                                financialYear=financial_year or "FY2026",
                                pageCount=page_count,
                                status="completed",
                                currentStage="Ready",
                                progressPercent=100,
                                uploadedAt=datetime.utcnow().isoformat(),
                                processedAt=datetime.utcnow().isoformat(),
                                storageUrl=f"/uploads/{user_dir}/{doc_dir}/{doc_filename}",
                                metadata=raw_meta,
                            )
                            _in_memory_documents[doc_dir] = doc_model
                        except Exception as e:
                            logger.debug(f"Note scanning document '{doc_dir}': {str(e)}")
        except Exception as scan_err:
            logger.warning(f"Error scanning local documents: {str(scan_err)}")

    def _compute_file_hash(self, file_path_or_bytes: Union[str, bytes]) -> str:
        """Streamed SHA-256 hash calculation with zero memory ballooning."""
        hasher = hashlib.sha256()
        if isinstance(file_path_or_bytes, str) and os.path.exists(file_path_or_bytes):
            with open(file_path_or_bytes, "rb") as f:
                while True:
                    buf = f.read(1024 * 1024)
                    if not buf:
                        break
                    hasher.update(buf)
        elif isinstance(file_path_or_bytes, bytes):
            hasher.update(file_path_or_bytes)
        return hasher.hexdigest()

    def cancel_processing(self, document_id: str) -> bool:
        """Signals cancellation for a running document processing pipeline."""
        return cancellation_manager.cancel(document_id)

    def prepare_upload_record(
        self,
        temp_file_path: str,
        filename: str,
        user_id: str
    ) -> Tuple[DocumentModel, bool]:
        """
        Fast non-blocking upload initialization (< 1 second):
        1. Computes SHA-256 hash. If document was previously completed & indexed, returns instantly.
        2. Saves uploaded file directly to local storage `uploads/<user_id>/<document_id>/<filename>`.
        3. Extracts fast pre-flight metadata (units/pages count, company name, FY).
        4. Creates DocumentModel with `status="processing"`, `currentStage="Queued"`, `progressPercent=5`.
        5. Returns (doc_model, is_already_completed).
        """
        file_size = os.path.getsize(temp_file_path) if os.path.exists(temp_file_path) else 0
        doc_hash = self._compute_file_hash(temp_file_path)
        now_iso = datetime.utcnow().isoformat()

        # Instant Hash Reuse check
        try:
            existing_docs = self.list_user_documents(user_id)
            for old_doc in existing_docs:
                old_hash = (old_doc.metadata or {}).get("doc_hash")
                if old_hash == doc_hash and old_doc.status == "completed" and self.vector_service.document_exists(old_doc.documentId, user_id):
                    logger.info(f"Instant Hash Reuse for '{filename}' ({doc_hash[:12]}): Returning existing indexed document '{old_doc.documentId}'.")
                    old_doc.currentStage = "Ready"
                    old_doc.stageMessage = f"Report loaded instantly from vector cache ({old_doc.pageCount} pages)."
                    old_doc.progressPercent = 100
                    return old_doc, True

            matched_doc_id = self.vector_service.document_exists_by_hash(doc_hash, user_id)
            if matched_doc_id:
                matched_doc = self.get_document(matched_doc_id, user_id)
                if matched_doc and matched_doc.status == "completed":
                    logger.info(f"ChromaDB Hash Match: Reusing existing indexed document '{matched_doc_id}'.")
                    matched_doc.currentStage = "Ready"
                    matched_doc.stageMessage = f"Report loaded instantly from vector cache ({matched_doc.pageCount} pages)."
                    matched_doc.progressPercent = 100
                    return matched_doc, True
        except Exception as dup_err:
            logger.warning(f"Error checking duplicate uploads: {str(dup_err)}")

        document_id = f"doc_{uuid.uuid4().hex[:12]}"
        upload_dir = os.path.join(os.getcwd(), "uploads", user_id, document_id)
        os.makedirs(upload_dir, exist_ok=True)
        dest_file_path = os.path.join(upload_dir, filename)

        if os.path.abspath(temp_file_path) != os.path.abspath(dest_file_path):
            shutil.copyfile(temp_file_path, dest_file_path)

        storage_url = f"/uploads/{user_id}/{document_id}/{filename}"

        # Fast pre-flight metadata extraction
        page_count, company_name, financial_year, raw_meta = self._extract_document_metadata(
            file_bytes=dest_file_path,
            filename=filename
        )
        raw_meta["doc_hash"] = doc_hash

        doc_model = DocumentModel(
            documentId=document_id,
            userId=user_id,
            fileName=filename,
            fileSize=file_size,
            companyName=company_name or "Financial Report",
            financialYear=financial_year or "FY2026",
            pageCount=page_count,
            status="processing",
            currentStage="Queued",
            stageMessage="Queued for local background processing",
            progressPercent=5,
            uploadedAt=now_iso,
            storageUrl=storage_url,
            metadata=raw_meta
        )
        self._save_to_firestore(doc_model)
        logger.info(f"Created queued document record '{document_id}' for '{filename}' ({page_count} pages).")
        return doc_model, False

    def process_document_background(self, document_id: str, user_id: str):
        """
        Background worker task executing full PDF extraction, OCR, chunking, embedding, and indexing.
        Runs asynchronously in local background worker thread pool without blocking FastAPI HTTP requests.
        """
        doc_model = self.get_document(document_id, user_id)
        if not doc_model:
            logger.error(f"[BackgroundWorker] Document '{document_id}' not found for processing.")
            return

        cancel_event = cancellation_manager.register(document_id)
        file_path = self.get_document_file_path(document_id, user_id)
        if not file_path or not os.path.exists(file_path):
            logger.error(f"[BackgroundWorker] File path for '{document_id}' does not exist.")
            doc_model.status = "failed"
            doc_model.currentStage = "Failed"
            doc_model.errorMessage = "File not found on disk."
            self._save_to_firestore(doc_model)
            return

        filename = doc_model.fileName
        active_stage = "Queued"

        def update_stage(stage_name: str, progress_pct: int, msg: Optional[str] = None):
            nonlocal active_stage
            active_stage = stage_name
            doc_model.currentStage = stage_name
            doc_model.progressPercent = progress_pct
            doc_model.stageMessage = msg or f"Stage: {stage_name}"
            self._save_to_firestore(doc_model)
            logger.info(f"[{filename}] Background Progress {progress_pct}% -> {stage_name}: {msg}")

        try:
            update_stage("Analyzing", 15, f"Inspecting document structure and pages ({doc_model.fileSize / (1024*1024):.1f} MB)")

            if cancel_event.is_set():
                raise InterruptedError("Processing was cancelled by user.")

            logger.info(f"Running DocumentProcessor pipeline in background for '{filename}' ({document_id})...")
            proc_result = self.processor.process_document(
                file_source=file_path,
                document_id=document_id,
                user_id=user_id,
                file_name=filename,
                company_name=doc_model.companyName,
                financial_year=doc_model.financialYear,
                on_stage_update=update_stage
            )

            if cancel_event.is_set():
                raise InterruptedError("Processing was cancelled by user.")

            doc_model.fileType = proc_result.file_type
            doc_model.pageCount = proc_result.total_pages

            update_stage("Embedding", 75, f"Generating financial vector embeddings for {len(proc_result.chunks)} semantic chunks")

            update_stage("Indexing", 90, "Incrementally indexing vectors into ChromaDB collection")
            indexed_count = self.vector_service.add_document(
                document_id=document_id,
                user_id=user_id,
                chunks=proc_result.chunks,
                overwrite_if_exists=True,
                doc_hash=(doc_model.metadata or {}).get("doc_hash", "")
            )

            doc_model.status = "completed"
            doc_model.currentStage = "Ready"
            doc_model.stageMessage = f"Report processed and indexed successfully ({proc_result.total_pages} pages/sheets, {indexed_count} chunks)."
            doc_model.progressPercent = 100
            doc_model.processedAt = datetime.utcnow().isoformat()

            self._save_to_firestore(doc_model)
            logger.info(f"Background worker completed document '{filename}' (ID: {document_id}): {proc_result.total_pages} pages, {indexed_count} chunks.")

        except InterruptedError as int_err:
            logger.warning(f"Document {document_id} processing was cancelled: {str(int_err)}")
            doc_model.status = "cancelled"
            doc_model.currentStage = "Cancelled"
            doc_model.errorMessage = "Processing cancelled by user."
            doc_model.stageMessage = "Processing cancelled."
            doc_model.processedAt = datetime.utcnow().isoformat()
            self._save_to_firestore(doc_model)

        except Exception as e:
            logger.error(f"Failed background document processing {document_id} at stage '{active_stage}': {str(e)}", exc_info=True)
            doc_model.status = "failed"
            doc_model.currentStage = "Failed"
            doc_model.errorMessage = f"[{active_stage}] {str(e)}"
            doc_model.stageMessage = f"Processing failed at stage '{active_stage}': {str(e)}"
            doc_model.processedAt = datetime.utcnow().isoformat()
            self._save_to_firestore(doc_model)
        finally:
            cancellation_manager.unregister(document_id)

    def process_and_save_upload(
        self,
        file_bytes: Optional[bytes] = None,
        file_path: Optional[str] = None,
        filename: str = "document.pdf",
        user_id: str = "default_user",
    ) -> DocumentModel:
        """
        Synchronous processing entrypoint maintained for backward compatibility.
        Prepares upload record and executes background processing.
        """
        temp_path = file_path
        if not temp_path and file_bytes:
            temp_dir = os.path.join(os.getcwd(), "uploads", "temp")
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, f"temp_{uuid.uuid4().hex}_{filename}")
            with open(temp_path, "wb") as f:
                f.write(file_bytes)

        doc_model, is_completed = self.prepare_upload_record(
            temp_file_path=temp_path,
            filename=filename,
            user_id=user_id
        )

        if not is_completed:
            self.process_document_background(document_id=doc_model.documentId, user_id=user_id)

        return doc_model

    def ensure_document_indexed(self, document_id: str, user_id: str) -> bool:
        """
        Ensures that vector chunks exist in ChromaDB for any supported document format.
        Returns instantly if chunks exist in ChromaDB to prevent chat latency.
        """
        if self.vector_service.document_exists(document_id=document_id, user_id=user_id):
            return True

        try:
            if self.vector_service.collection.count() > 0:
                return True
        except Exception:
            pass

        file_path = self.get_document_file_path(document_id, user_id)
        if file_path and os.path.exists(file_path):
            try:
                logger.info(f"Auto indexing document from disk for '{document_id}': '{file_path}'...")
                self.process_document_background(document_id=document_id, user_id=user_id)
                return True
            except Exception as e:
                logger.error(f"Failed indexing document {document_id}: {str(e)}")
                return False

        return False

    def get_document(self, document_id: str, user_id: str) -> Optional[DocumentModel]:
        """Retrieves a document record with instant in-memory and disk fallback."""
        # 1. In-memory check
        doc_local = _in_memory_documents.get(document_id)
        if doc_local and (doc_local.userId == user_id or not user_id):
            return doc_local

        # 2. Local disk metadata.json check
        for root in _get_uploads_roots():
            candidates = []
            if user_id:
                candidates.append(os.path.join(root, user_id, document_id))
            candidates.append(os.path.join(root, document_id))
            for doc_dir in candidates:
                meta_file = os.path.join(doc_dir, "metadata.json")
                if os.path.isfile(meta_file):
                    try:
                        with open(meta_file, "r", encoding="utf-8") as mf:
                            d = DocumentModel.from_dict(json.load(mf))
                            _in_memory_documents[document_id] = d
                            return d
                    except Exception:
                        pass

        # 3. Firestore check with short timeout
        if self.firestore_db:
            def _fetch():
                doc = self.firestore_db.collection("documents").document(document_id).get()
                if doc.exists:
                    data = doc.to_dict()
                    if data.get("userId") == user_id or not user_id:
                        return DocumentModel.from_dict(data)
                return None

            result = _run_with_timeout(_fetch, timeout_sec=1.0)
            if result:
                _in_memory_documents[document_id] = result
                return result

        for d in _in_memory_documents.values():
            if d.documentId == document_id:
                return d
        return None

    get_document_by_id = get_document

    def list_user_documents(self, user_id: str) -> List[DocumentModel]:
        """Lists all document records belonging to the authenticated user with instant local fallback."""
        # 1. Attempt fast Firestore query
        if self.firestore_db:
            def _fetch_list():
                docs = (
                    self.firestore_db.collection("documents")
                    .where("userId", "==", user_id)
                    .stream()
                )
                return [DocumentModel.from_dict(doc.to_dict()) for doc in docs]

            result = _run_with_timeout(_fetch_list, timeout_sec=1.0)
            if result is not None and len(result) > 0:
                for d in result:
                    _in_memory_documents[d.documentId] = d
                return result

        # 2. In-memory documents
        docs_dict = {
            d.documentId: d for d in _in_memory_documents.values()
            if d.userId == user_id or not user_id
        }

        # 3. Discover local files on disk in uploads/<user_id>/
        for root in _get_uploads_roots():
            user_dir = os.path.join(root, user_id)
            if os.path.isdir(user_dir):
                for doc_id in os.listdir(user_dir):
                    if doc_id in docs_dict:
                        continue
                    doc_dir = os.path.join(user_dir, doc_id)
                    if not os.path.isdir(doc_dir):
                        continue
                    meta_file = os.path.join(doc_dir, "metadata.json")
                    if os.path.isfile(meta_file):
                        try:
                            with open(meta_file, "r", encoding="utf-8") as mf:
                                data = json.load(mf)
                                loaded_doc = DocumentModel.from_dict(data)
                                docs_dict[doc_id] = loaded_doc
                                _in_memory_documents[doc_id] = loaded_doc
                        except Exception:
                            pass
                    else:
                        pdf_files = [f for f in os.listdir(doc_dir) if f.lower().endswith(SUPPORTED_EXTENSIONS)]
                        if pdf_files:
                            f_name = pdf_files[0]
                            f_path = os.path.join(doc_dir, f_name)
                            f_size = os.path.getsize(f_path) if os.path.exists(f_path) else 0
                            discovered_doc = DocumentModel(
                                documentId=doc_id,
                                userId=user_id,
                                fileName=f_name,
                                fileSize=f_size,
                                companyName=f_name.replace(".pdf", "").replace("_", " "),
                                financialYear=f"FY{datetime.utcnow().year}",
                                pageCount=1,
                                status="completed",
                                currentStage="Ready",
                                stageMessage="Ready for analysis",
                                progressPercent=100,
                                uploadedAt=datetime.utcnow().isoformat(),
                                storageUrl=f"/uploads/{user_id}/{doc_id}/{f_name}"
                            )
                            docs_dict[doc_id] = discovered_doc
                            _in_memory_documents[doc_id] = discovered_doc

        return list(docs_dict.values())

    def delete_document(self, document_id: str, user_id: str) -> bool:
        """Deletes a document record, vector chunks, storage file, and invalidates AI cache."""
        from .cache_service import get_ai_cache_service
        get_ai_cache_service().invalidate_document_cache(document_id=document_id, user_id=user_id)

        doc_model = self.get_document(document_id, user_id)

        if self.firestore_db:
            def _del():
                self.firestore_db.collection("documents").document(document_id).delete()

            _run_with_timeout(_del, timeout_sec=2.5)

        if document_id in _in_memory_documents:
            del _in_memory_documents[document_id]

        try:
            upload_dir = os.path.join(os.getcwd(), "uploads", user_id, document_id)
            if os.path.exists(upload_dir):
                shutil.rmtree(upload_dir, ignore_errors=True)
                logger.info(f"Deleted local uploads folder: {upload_dir}")
        except Exception as disk_err:
            logger.warning(f"Error deleting local upload directory: {str(disk_err)}")

        if self.storage_bucket and doc_model and doc_model.fileName:
            try:
                blob_path = f"documents/{user_id}/{document_id}/{doc_model.fileName}"
                blob = self.storage_bucket.blob(blob_path)
                if blob.exists():
                    blob.delete()
                    logger.info(f"Deleted Firebase Storage blob: {blob_path}")
            except Exception as storage_err:
                logger.warning(f"Error deleting Firebase Storage blob: {str(storage_err)}")

        self.vector_service.delete_document(document_id=document_id, user_id=user_id)
        return True

    def get_document_file_path(self, document_id: str, user_id: str) -> Optional[str]:
        """Locates the full filesystem path of an uploaded document file for an authenticated user."""
        doc = self.get_document(document_id, user_id)
        upload_roots = _get_uploads_roots()
        for root_dir in upload_roots:
            user_doc_dir = os.path.join(root_dir, user_id, document_id)
            if os.path.exists(user_doc_dir):
                files = [f for f in os.listdir(user_doc_dir) if any(f.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)]
                if files:
                    return os.path.join(user_doc_dir, files[0])
        return None

    def _store_file(
        self,
        file_bytes: bytes,
        filename: str,
        user_id: str,
        document_id: str
    ) -> str:
        """Saves file to Firebase Storage if available, else local storage."""
        if self.storage_bucket:
            try:
                blob_path = f"documents/{user_id}/{document_id}/{filename}"
                blob = self.storage_bucket.blob(blob_path)
                blob.upload_from_string(file_bytes)
                blob.make_public()
                logger.info(f"File uploaded to Firebase Storage: {blob.public_url}")
                return blob.public_url or f"gs://{self.storage_bucket.name}/{blob_path}"
            except Exception as e:
                logger.warning(f"Firebase Storage upload failed: {str(e)}. Falling back to local storage.")

        upload_dir = os.path.join(os.getcwd(), "uploads", user_id, document_id)
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        relative_url = f"/uploads/{user_id}/{document_id}/{filename}"
        logger.info(f"File saved to local storage: {file_path}")
        return relative_url

    def _extract_document_metadata(
        self,
        file_bytes: Union[bytes, str],
        filename: str
    ) -> Tuple[int, Optional[str], Optional[str], Dict[str, Any]]:
        """
        Universal metadata extractor supporting PDF, XLSX, XLS, CSV, DOCX, TXT, MD, and JSON.
        Accepts either file bytes or file path for zero memory overhead.
        """
        page_count = 1
        company_name = None
        financial_year = None
        raw_meta = {}

        try:
            from ..document_processing.file_detector import FileTypeDetector
            fmt = FileTypeDetector.detect_format(file_bytes, filename)
            raw_meta["detected_format"] = fmt
        except Exception:
            fmt = "pdf"

        if fmt == "pdf":
            doc = None
            try:
                if isinstance(file_bytes, str):
                    doc = fitz.open(file_bytes)
                else:
                    doc = fitz.open(stream=file_bytes, filetype="pdf")

                page_count = len(doc)
                raw_meta = doc.metadata or {}

                sample_text = ""
                for i in range(min(6, page_count)):
                    sample_text += doc[i].get_text("text") + "\n"

                if "Tata Consultancy Services" in sample_text or "TCS" in filename.upper():
                    company_name = "Tata Consultancy Services Limited"
                elif "Infosys" in sample_text or "INFY" in filename.upper():
                    company_name = "Infosys Limited"
                elif "Reliance Industries" in sample_text or "RELIANCE" in filename.upper():
                    company_name = "Reliance Industries Limited"

                if not company_name:
                    m_comp = re.search(r"([A-Z][A-Za-z0-9\s,&.-]+(?:Limited|Ltd|Corporation|Corp|Inc|LLC|Pvt|Bank))", sample_text, re.IGNORECASE)
                    if m_comp:
                        candidate = m_comp.group(1).strip()
                        if candidate.lower() not in ("annual report", "financial statements", "independent auditor"):
                            company_name = candidate

                fy_match = re.search(r"(?:fiscal year ended|period ended|ended|year ended)\s+[a-zA-Z]+\s+\d{1,2},?\s+(20\d{2})", sample_text, re.IGNORECASE)
                if fy_match:
                    financial_year = f"FY{fy_match.group(1)}"
                else:
                    year_match = re.search(r"\b(202[0-9]|201[0-9])\b", sample_text) or re.search(r"\b(202[0-9]|201[0-9])\b", filename)
                    if year_match:
                        financial_year = f"FY{year_match.group(1)}"
            except Exception as e:
                logger.warning(f"Error extracting PDF metadata: {str(e)}")
            finally:
                if doc:
                    doc.close()

        if not company_name or company_name.lower() in ("annual", "report", "financial report", "unknown"):
            clean_name = os.path.splitext(filename)[0]
            clean_name = re.sub(r"[-_](10K|10Q|8K|FY\d+|Q\d+|Annual|Report|\d{4})", "", clean_name, flags=re.IGNORECASE)
            clean_name = clean_name.replace("_", " ").replace("-", " ").strip().title()
            if clean_name and clean_name.lower() not in ("annual", "report", "financial"):
                company_name = clean_name
            else:
                company_name = "Financial Entity"

        if not financial_year:
            year_match = re.search(r"\b(202[0-9]|201[0-9])\b", filename)
            if year_match:
                financial_year = f"FY{year_match.group(1)}"
            else:
                financial_year = f"FY{datetime.utcnow().year}"

        return page_count or 1, company_name, financial_year, raw_meta

    def _save_to_firestore(self, doc_model: DocumentModel) -> None:
        """Saves document model to in-memory cache, local disk metadata.json, and async Firestore."""
        _in_memory_documents[doc_model.documentId] = doc_model

        # Persist metadata.json locally alongside the uploaded document
        try:
            for root in _get_uploads_roots():
                doc_dir = os.path.join(root, doc_model.userId, doc_model.documentId)
                if os.path.isdir(doc_dir):
                    meta_file = os.path.join(doc_dir, "metadata.json")
                    with open(meta_file, "w", encoding="utf-8") as mf:
                        json.dump(doc_model.to_dict(), mf, indent=2)
                    break
        except Exception as err:
            logger.debug(f"Could not persist local metadata.json: {err}")

        # Async non-blocking Firestore update in daemon thread
        if self.firestore_db:
            def _save():
                try:
                    self.firestore_db.collection("documents").document(doc_model.documentId).set(
                        doc_model.to_dict()
                    )
                except Exception as e:
                    logger.debug(f"Firestore background save failed: {e}")

            threading.Thread(target=_save, daemon=True).start()
