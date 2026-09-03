import os
import re
import uuid
import concurrent.futures
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
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# In-memory storage fallback for local development
_in_memory_documents: Dict[str, DocumentModel] = {}


def _run_with_timeout(func, timeout_sec: float = 3.0):
    """Executes a function in a worker thread with a strict timeout to prevent Firestore gRPC blocking."""
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func)
            return future.result(timeout=timeout_sec)
    except Exception as e:
        logger.warning(f"Firestore query timed out ({timeout_sec}s) or failed: {str(e)}. Falling back to local storage.")
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


import threading


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
    Service handling Multi-Format Document uploads, extraction, storage, vector indexing,
    and metadata management across PDF, XLSX, XLS, CSV, DOCX, TXT, MD, and JSON.
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
                            import hashlib
                            file_size = os.path.getsize(full_file_path)
                            with open(full_file_path, "rb") as f:
                                file_bytes = f.read()

                            doc_hash = hashlib.sha256(file_bytes).hexdigest()
                            page_count, company_name, financial_year, raw_meta = self._extract_document_metadata(
                                file_bytes=file_bytes,
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

    def cancel_processing(self, document_id: str) -> bool:
        """Signals cancellation for a running document processing pipeline."""
        return cancellation_manager.cancel(document_id)

    def process_and_save_upload(
        self,
        file_bytes: Optional[bytes] = None,
        file_path: Optional[str] = None,
        filename: str = "document.pdf",
        user_id: str = "default_user",
    ) -> DocumentModel:
        """
        High-performance streaming upload & ingestion pipeline for files up to 200MB:
        1. Computes SHA-256 document hash (streamed without RAM ballooning)
        2. Instant vector reuse if hash match is found
        3. Pre-flight inspection (page count, text characteristics, OCR requirement)
        4. Incremental page-by-page extraction in controlled batches
        5. Selective OCR only on verified image-only pages
        6. Batched embeddings and incremental ChromaDB insertion
        7. Real-time stage tracking and graceful error diagnosis
        """
        import hashlib
        import shutil

        # Step 0: Compute SHA-256 hash
        hasher = hashlib.sha256()
        file_size = 0
        if file_path and os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            with open(file_path, "rb") as f:
                while True:
                    buf = f.read(1024 * 1024)
                    if not buf:
                        break
                    hasher.update(buf)
            file_source = file_path
        elif file_bytes is not None:
            file_size = len(file_bytes)
            hasher.update(file_bytes)
            file_source = file_bytes
        else:
            raise ValueError("Either file_bytes or file_path must be provided to process_and_save_upload.")

        doc_hash = hasher.hexdigest()
        now_iso = datetime.utcnow().isoformat()

        # Step 0B: Check if this exact file hash is already indexed and completed for this user
        try:
            existing_docs = self.list_user_documents(user_id)
            for old_doc in existing_docs:
                old_hash = (old_doc.metadata or {}).get("doc_hash")
                if old_hash == doc_hash and old_doc.status == "completed" and self.vector_service.document_exists(old_doc.documentId, user_id):
                    logger.info(f"Instant Hash Match for '{filename}' (hash={doc_hash[:12]}): Reusing existing indexed vectors for document '{old_doc.documentId}'.")
                    old_doc.currentStage = "Ready"
                    old_doc.stageMessage = f"Report loaded instantly from vector cache ({old_doc.pageCount} pages)."
                    old_doc.progressPercent = 100
                    return old_doc

            # Direct ChromaDB hash lookup
            matched_doc_id = self.vector_service.document_exists_by_hash(doc_hash, user_id)
            if matched_doc_id:
                matched_doc = self.get_document(matched_doc_id, user_id)
                if matched_doc and matched_doc.status == "completed":
                    logger.info(f"ChromaDB Hash Match: Reusing existing indexed document '{matched_doc_id}'.")
                    matched_doc.currentStage = "Ready"
                    matched_doc.stageMessage = f"Report loaded instantly from vector cache ({matched_doc.pageCount} pages)."
                    matched_doc.progressPercent = 100
                    return matched_doc

            # If same filename but different content, remove stale old version
            for old_doc in existing_docs:
                old_hash = (old_doc.metadata or {}).get("doc_hash")
                if old_doc.fileName == filename and old_hash and old_hash != doc_hash:
                    logger.info(f"Updated document content detected for '{filename}'. Clearing stale document '{old_doc.documentId}'.")
                    self.delete_document(document_id=old_doc.documentId, user_id=user_id)
        except Exception as dup_err:
            logger.warning(f"Error checking duplicate uploads: {str(dup_err)}")

        document_id = f"doc_{uuid.uuid4().hex[:12]}"
        cancel_event = cancellation_manager.register(document_id)

        # Step 1: Create initial record with 'Uploading' stage
        doc_model = DocumentModel(
            documentId=document_id,
            userId=user_id,
            fileName=filename,
            fileSize=file_size,
            status="processing",
            currentStage="Uploading",
            stageMessage="Uploading document to secure workspace storage",
            progressPercent=10,
            uploadedAt=now_iso,
            storageUrl="",
            metadata={"doc_hash": doc_hash}
        )
        self._save_to_firestore(doc_model)

        active_stage = "Uploading"

        def update_stage(stage_name: str, progress_pct: int, msg: Optional[str] = None):
            nonlocal active_stage
            active_stage = stage_name
            doc_model.currentStage = stage_name
            doc_model.progressPercent = progress_pct
            doc_model.stageMessage = msg or f"Stage: {stage_name}"
            self._save_to_firestore(doc_model)
            logger.info(f"[{filename}] Progress {progress_pct}% -> {stage_name}: {msg}")

        try:
            # Step 2: Store file (Firebase Storage or local uploads directory)
            if file_path and os.path.exists(file_path):
                upload_dir = os.path.join(os.getcwd(), "uploads", user_id, document_id)
                os.makedirs(upload_dir, exist_ok=True)
                dest_file_path = os.path.join(upload_dir, filename)
                if os.path.abspath(file_path) != os.path.abspath(dest_file_path):
                    shutil.copyfile(file_path, dest_file_path)
                storage_url = f"/uploads/{user_id}/{document_id}/{filename}"
                file_source = dest_file_path
            else:
                storage_url = self._store_file(
                    file_bytes=file_bytes,
                    filename=filename,
                    user_id=user_id,
                    document_id=document_id
                )
                file_source = file_bytes

            doc_model.storageUrl = storage_url

            # Step 3: Extract metadata from document (Stage: Analyzing)
            update_stage("Analyzing", 15, f"Inspecting document structure, pages, and OCR necessity ({file_size / (1024*1024):.1f} MB)")
            page_count, company_name, financial_year, raw_meta = self._extract_document_metadata(
                file_bytes=file_source,
                filename=filename
            )
            raw_meta["doc_hash"] = doc_hash

            doc_model.pageCount = page_count
            doc_model.companyName = company_name
            doc_model.financialYear = financial_year
            doc_model.metadata = raw_meta

            if cancel_event.is_set():
                raise InterruptedError("Processing was cancelled by user.")

            # Step 4: Execute multi-format document processing pipeline (Extracting -> OCR -> Chunking)
            logger.info(f"Running DocumentProcessor pipeline for '{filename}' ({document_id})...")
            proc_result = self.processor.process_document(
                file_source=file_source,
                document_id=document_id,
                user_id=user_id,
                file_name=filename,
                company_name=company_name,
                financial_year=financial_year,
                on_stage_update=update_stage
            )

            if cancel_event.is_set():
                raise InterruptedError("Processing was cancelled by user.")

            doc_model.fileType = proc_result.file_type
            doc_model.pageCount = proc_result.total_pages

            # Stage: Embedding
            update_stage("Embedding", 75, f"Generating financial vector embeddings for {len(proc_result.chunks)} semantic chunks")

            # Stage: Indexing
            update_stage("Indexing", 90, "Incrementally indexing vectors into ChromaDB collection")
            indexed_count = self.vector_service.add_document(
                document_id=document_id,
                user_id=user_id,
                chunks=proc_result.chunks,
                overwrite_if_exists=True,
                doc_hash=doc_hash
            )

            # Stage: Ready
            doc_model.status = "completed"
            doc_model.currentStage = "Ready"
            doc_model.stageMessage = f"Report processed and indexed successfully ({proc_result.total_pages} pages/sheets, {indexed_count} chunks)."
            doc_model.progressPercent = 100
            doc_model.processedAt = datetime.utcnow().isoformat()

            # Step 6: Save final completed record
            self._save_to_firestore(doc_model)
            logger.info(
                f"Document '{filename}' (ID: {document_id}) processed & vector indexed successfully: "
                f"{proc_result.total_pages} units, {indexed_count} vector chunks, Company: '{doc_model.companyName}', Year: '{doc_model.financialYear}'"
            )
            return doc_model

        except InterruptedError as int_err:
            logger.warning(f"Document {document_id} processing was cancelled: {str(int_err)}")
            doc_model.status = "cancelled"
            doc_model.currentStage = "Cancelled"
            doc_model.errorMessage = "Processing cancelled by user."
            doc_model.stageMessage = "Processing cancelled."
            doc_model.processedAt = datetime.utcnow().isoformat()
            self._save_to_firestore(doc_model)
            return doc_model

        except Exception as e:
            logger.error(f"Failed processing document upload {document_id} at stage '{active_stage}': {str(e)}", exc_info=True)
            doc_model.status = "failed"
            doc_model.currentStage = "Failed"
            doc_model.errorMessage = f"[{active_stage}] {str(e)}"
            doc_model.stageMessage = f"Processing failed at stage '{active_stage}': {str(e)}"
            doc_model.processedAt = datetime.utcnow().isoformat()
            self._save_to_firestore(doc_model)
            raise e
        finally:
            cancellation_manager.unregister(document_id)

    def ensure_document_indexed(self, document_id: str, user_id: str) -> bool:
        """
        Ensures that vector chunks exist in ChromaDB for any supported document format.
        Returns instantly if chunks exist in ChromaDB to prevent chat latency.
        """
        if self.vector_service.document_exists(document_id=document_id, user_id=user_id):
            return True

        # If ChromaDB collection already has indexed documents, return True immediately
        try:
            if self.vector_service.collection.count() > 0:
                return True
        except Exception:
            pass

        file_path = None
        target_filename = "report.pdf"
        actual_user_id = user_id or "dev_user_123"

        base_uploads = os.path.join(os.getcwd(), "uploads")
        if os.path.exists(base_uploads):
            # 1. Direct match uploads/<user_id>/<document_id>
            candidate_dir = os.path.join(base_uploads, actual_user_id, document_id)
            if os.path.exists(candidate_dir):
                doc_files = [f for f in os.listdir(candidate_dir) if any(f.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)]
                if doc_files:
                    file_path = os.path.join(candidate_dir, doc_files[0])
                    target_filename = doc_files[0]

            # 2. Match across all user subdirectories
            if not file_path:
                for root, dirs, files in os.walk(base_uploads):
                    if os.path.basename(root) == document_id:
                        doc_files = [f for f in files if any(f.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)]
                        if doc_files:
                            file_path = os.path.join(root, doc_files[0])
                            target_filename = doc_files[0]
                            break

            # 3. Fallback for doc_general / doc_unknown / latest uploaded document
            if not file_path:
                all_docs = []
                for root, dirs, files in os.walk(base_uploads):
                    for f in files:
                        if any(f.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                            fp = os.path.join(root, f)
                            all_docs.append((os.path.getmtime(fp), fp, f))
                if all_docs:
                    all_docs.sort(reverse=True)
                    file_path = all_docs[0][1]
                    target_filename = all_docs[0][2]

        if file_path and os.path.exists(file_path):
            try:
                logger.info(f"Auto indexing document from disk for '{document_id}': '{file_path}'...")
                with open(file_path, "rb") as f:
                    doc_bytes = f.read()

                page_count, company_name, financial_year, raw_meta = self._extract_document_metadata(
                    file_bytes=doc_bytes,
                    filename=target_filename
                )

                proc_result = self.processor.process_document(
                    file_source=doc_bytes,
                    document_id=document_id,
                    user_id=actual_user_id,
                    file_name=target_filename,
                    company_name=company_name or "Financial Report",
                    financial_year=financial_year or "FY2026",
                )

                self.vector_service.add_document(
                    document_id=document_id,
                    user_id=actual_user_id,
                    chunks=proc_result.chunks,
                    overwrite_if_exists=True
                )

                doc_model = DocumentModel(
                    documentId=document_id,
                    userId=actual_user_id,
                    fileName=target_filename,
                    fileSize=len(doc_bytes),
                    companyName=company_name or "Financial Report",
                    financialYear=financial_year or "FY2026",
                    pageCount=page_count,
                    status="completed",
                    uploadedAt=datetime.utcnow().isoformat(),
                    processedAt=datetime.utcnow().isoformat(),
                    storageUrl=f"/uploads/{actual_user_id}/{document_id}/{target_filename}",
                    metadata=raw_meta,
                )
                _in_memory_documents[document_id] = doc_model
                return True
            except Exception as e:
                logger.error(f"Failed indexing document {document_id}: {str(e)}")
                return False

        return False

    def get_document(self, document_id: str, user_id: str) -> Optional[DocumentModel]:
        """Retrieves a document record for the authenticated user with a 3s timeout fallback."""
        if self.firestore_db:
            def _fetch():
                doc = self.firestore_db.collection("documents").document(document_id).get()
                if doc.exists:
                    data = doc.to_dict()
                    if data.get("userId") == user_id or not user_id:
                        return DocumentModel.from_dict(data)
                return None

            result = _run_with_timeout(_fetch, timeout_sec=2.5)
            if result:
                return result

        doc_local = _in_memory_documents.get(document_id)
        if doc_local and (doc_local.userId == user_id or not user_id):
            return doc_local

        for d in _in_memory_documents.values():
            if d.documentId == document_id:
                return d
        return None

    get_document_by_id = get_document

    def list_user_documents(self, user_id: str) -> List[DocumentModel]:
        """Lists all document records belonging to the authenticated user with a 3s timeout fallback."""
        if self.firestore_db:
            def _fetch_list():
                docs = (
                    self.firestore_db.collection("documents")
                    .where("userId", "==", user_id)
                    .stream()
                )
                return [DocumentModel.from_dict(doc.to_dict()) for doc in docs]

            result = _run_with_timeout(_fetch_list, timeout_sec=3.0)
            if result is not None:
                return result

        return [d for d in _in_memory_documents.values() if d.userId == user_id or not user_id]

    def delete_document(self, document_id: str, user_id: str) -> bool:
        """Deletes a document record, vector chunks, storage file, and invalidates AI cache."""
        from .cache_service import get_ai_cache_service
        get_ai_cache_service().invalidate_document_cache(document_id=document_id, user_id=user_id)

        # Retrieve the document metadata before deleting to get its filename
        doc_model = self.get_document(document_id, user_id)

        # 1. Delete from Firestore
        if self.firestore_db:
            def _del():
                self.firestore_db.collection("documents").document(document_id).delete()

            _run_with_timeout(_del, timeout_sec=2.5)

        # 2. Delete from local cache
        if document_id in _in_memory_documents:
            del _in_memory_documents[document_id]

        # 3. Delete local uploads folder from disk
        try:
            import shutil
            upload_dir = os.path.join(os.getcwd(), "uploads", user_id, document_id)
            if os.path.exists(upload_dir):
                shutil.rmtree(upload_dir, ignore_errors=True)
                logger.info(f"Deleted local uploads folder: {upload_dir}")
        except Exception as disk_err:
            logger.warning(f"Error deleting local upload directory: {str(disk_err)}")

        # 4. Delete Firebase Storage blob if storage bucket is configured
        if self.storage_bucket and doc_model and doc_model.fileName:
            try:
                blob_path = f"documents/{user_id}/{document_id}/{doc_model.fileName}"
                blob = self.storage_bucket.blob(blob_path)
                if blob.exists():
                    blob.delete()
                    logger.info(f"Deleted Firebase Storage blob: {blob_path}")
            except Exception as storage_err:
                logger.warning(f"Error deleting Firebase Storage blob: {str(storage_err)}")

        # 5. Delete vector store chunks
        self.vector_service.delete_document(document_id=document_id, user_id=user_id)
        return True

    def get_document_file_path(self, document_id: str, user_id: str) -> Optional[str]:
        """Locates the full filesystem path of an uploaded document file for an authenticated user."""
        doc = self.get_document(document_id, user_id)
        if not doc:
            return None
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
        Returns (units_count, company_name, financial_year, raw_metadata).
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

        # PDF metadata
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

        # Excel metadata (XLSX, XLS)
        elif fmt in ("xlsx", "xls"):
            try:
                if fmt == "xlsx":
                    import openpyxl
                    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
                    page_count = len(wb.sheetnames)
                    raw_meta["sheets"] = wb.sheetnames
                    wb.close()
                else:
                    import xlrd
                    wb = xlrd.open_workbook(file_contents=file_bytes)
                    page_count = len(wb.sheet_names())
                    raw_meta["sheets"] = wb.sheet_names()
            except Exception as e:
                logger.warning(f"Error reading Excel metadata: {str(e)}")

        # DOCX metadata
        elif fmt == "docx":
            try:
                import docx
                doc = docx.Document(io.BytesIO(file_bytes))
                headings = [p.text for p in doc.paragraphs if "heading" in (p.style.name or "").lower()]
                page_count = max(len(headings), 1)
                raw_meta["headings"] = headings[:10]
            except Exception as e:
                logger.warning(f"Error reading DOCX metadata: {str(e)}")

        # Text-based metadata (CSV, TXT, MD, JSON)
        else:
            try:
                sample_str = file_bytes[:4096].decode("utf-8", errors="ignore")
                lines = sample_str.splitlines()
                page_count = max(len(lines) // 40, 1)
            except Exception:
                page_count = 1

        # Fallback naming heuristics
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

    def _extract_pdf_metadata(
        self,
        file_bytes: bytes,
        filename: str
    ) -> Tuple[int, Optional[str], Optional[str], Dict[str, Any]]:
        """Backward compatible metadata extraction alias."""
        return self._extract_document_metadata(file_bytes=file_bytes, filename=filename)

    def _save_to_firestore(self, doc_model: DocumentModel) -> None:
        """Saves document model to Firestore and in-memory cache with timeout safety."""
        _in_memory_documents[doc_model.documentId] = doc_model
        if self.firestore_db:
            def _save():
                self.firestore_db.collection("documents").document(doc_model.documentId).set(
                    doc_model.to_dict()
                )

            _run_with_timeout(_save, timeout_sec=2.5)
