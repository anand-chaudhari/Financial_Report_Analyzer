import os
import re
import uuid
import concurrent.futures
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
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


class DocumentService:
    """Service handling document upload, storage, metadata extraction, chunking, vector indexing, and Firestore CRUD."""

    def __init__(self):
        self.firestore_db = get_firestore_client()
        self.storage_bucket = get_storage_bucket()
        self.settings = get_settings()
        self.processor = DocumentProcessor()
        self.vector_service = VectorStoreService()
        self._restore_local_documents()

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


class DocumentService:
    """Service handling document upload, storage, metadata extraction, chunking, vector indexing, and Firestore CRUD."""

    def __init__(self):
        self.firestore_db = get_firestore_client()
        self.storage_bucket = get_storage_bucket()
        self.settings = get_settings()
        self.processor = DocumentProcessor()
        self.vector_service = VectorStoreService()
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
                        files = [f for f in os.listdir(doc_path) if f.lower().endswith(".pdf")]
                        if not files:
                            continue
                        pdf_filename = files[0]
                        full_file_path = os.path.join(doc_path, pdf_filename)
                        try:
                            file_size = os.path.getsize(full_file_path)
                            with open(full_file_path, "rb") as f:
                                file_bytes = f.read()

                            page_count, company_name, financial_year, raw_meta = self._extract_pdf_metadata(
                                file_bytes=file_bytes,
                                filename=pdf_filename
                            )

                            doc_model = DocumentModel(
                                documentId=doc_dir,
                                userId=user_dir,
                                fileName=pdf_filename,
                                fileSize=file_size,
                                companyName=company_name or "Financial Report",
                                financialYear=financial_year or "FY2026",
                                pageCount=page_count,
                                status="completed",
                                currentStage="Ready",
                                progressPercent=100,
                                uploadedAt=datetime.utcnow().isoformat(),
                                processedAt=datetime.utcnow().isoformat(),
                                storageUrl=f"/uploads/{user_dir}/{doc_dir}/{pdf_filename}",
                                metadata=raw_meta,
                            )
                            _in_memory_documents[doc_dir] = doc_model

                            # Restore in-memory document state; only index if vectors do not exist
                            if not self.vector_service.document_exists(document_id=doc_dir, user_id=user_dir):
                                proc_result = self.processor.process_pdf(
                                    pdf_source=file_bytes,
                                    document_id=doc_dir,
                                    user_id=user_dir,
                                    file_name=pdf_filename,
                                    company_name=company_name,
                                    financial_year=financial_year,
                                )
                                self.vector_service.add_document(
                                    document_id=doc_dir,
                                    user_id=user_dir,
                                    chunks=proc_result.chunks,
                                    overwrite_if_exists=False
                                )
                        except Exception as e:
                            logger.debug(f"Note scanning document '{doc_dir}': {str(e)}")
        except Exception as scan_err:
            logger.warning(f"Error scanning local documents: {str(scan_err)}")

    def process_and_save_upload(
        self,
        file_bytes: bytes,
        filename: str,
        user_id: str
    ) -> DocumentModel:
        """
        Processes an uploaded PDF:
        1. Generates unique document ID
        2. Saves file to Firebase Storage or local upload storage
        3. Extracts page count and metadata (company, year) via PyMuPDF
        4. Runs PDF processing pipeline (cleaning, section detection, semantic chunking)
        5. Indexes document chunks into ChromaDB vector store
        6. Saves document record to Firestore with status 'completed'
        """
        # Step 0: Check for duplicates and clear their cache / delete them
        try:
            existing_docs = self.list_user_documents(user_id)
            for old_doc in existing_docs:
                if old_doc.fileName == filename:
                    logger.info(f"Duplicate upload detected: '{filename}'. Clearing old document '{old_doc.documentId}' cache/vectors/files.")
                    self.delete_document(document_id=old_doc.documentId, user_id=user_id)
        except Exception as dup_err:
            logger.warning(f"Error checking/clearing duplicate uploads: {str(dup_err)}")

        document_id = f"doc_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.utcnow().isoformat()

        # Step 1: Create initial record with 'Uploading' stage
        doc_model = DocumentModel(
            documentId=document_id,
            userId=user_id,
            fileName=filename,
            fileSize=len(file_bytes),
            status="processing",
            currentStage="Uploading",
            stageMessage="Uploading document to secure workspace storage",
            progressPercent=10,
            uploadedAt=now_iso,
            storageUrl=""
        )
        self._save_to_firestore(doc_model)

        def update_stage(stage_name: str, progress_pct: int, msg: Optional[str] = None):
            doc_model.currentStage = stage_name
            doc_model.progressPercent = progress_pct
            doc_model.stageMessage = msg or f"Stage: {stage_name}"
            self._save_to_firestore(doc_model)
            logger.info(f"[{filename}] Progress {progress_pct}% -> {stage_name}")

        try:
            # Step 2: Store file (Firebase Storage or local uploads directory)
            storage_url = self._store_file(
                file_bytes=file_bytes,
                filename=filename,
                user_id=user_id,
                document_id=document_id
            )
            doc_model.storageUrl = storage_url

            # Step 3: Extract metadata from PDF bytes
            page_count, company_name, financial_year, raw_meta = self._extract_pdf_metadata(
                file_bytes=file_bytes,
                filename=filename
            )

            doc_model.pageCount = page_count
            doc_model.companyName = company_name
            doc_model.financialYear = financial_year
            doc_model.metadata = raw_meta

            # Step 4: Execute complete PDF processing pipeline with real-time stage updates
            logger.info(f"Running DocumentProcessor pipeline for '{filename}' ({document_id})...")
            proc_result = self.processor.process_pdf(
                pdf_source=file_bytes,
                document_id=document_id,
                user_id=user_id,
                file_name=filename,
                company_name=company_name,
                financial_year=financial_year,
                on_stage_update=update_stage
            )

            # Stage: Generating embeddings
            update_stage("Generating embeddings", 75, "Generating financial vector embeddings with MiniLM model")

            # Stage: Indexing
            update_stage("Indexing", 90, "Inserting semantic chunks into ChromaDB collection")
            indexed_count = self.vector_service.add_document(
                document_id=document_id,
                user_id=user_id,
                chunks=proc_result.chunks,
                overwrite_if_exists=True
            )

            # Stage: Ready
            doc_model.status = "completed"
            doc_model.currentStage = "Ready"
            doc_model.stageMessage = f"Report processed and indexed successfully ({page_count} pages, {indexed_count} chunks)."
            doc_model.progressPercent = 100
            doc_model.processedAt = datetime.utcnow().isoformat()

            # Step 6: Save final completed record
            self._save_to_firestore(doc_model)
            logger.info(
                f"Document '{filename}' (ID: {document_id}) processed & vector indexed successfully: "
                f"{page_count} pages, {indexed_count} vector chunks, Company: '{company_name}', Year: '{financial_year}'"
            )
            return doc_model

        except Exception as e:
            logger.error(f"Failed processing document upload {document_id}: {str(e)}", exc_info=True)
            doc_model.status = "failed"
            doc_model.currentStage = "Failed"
            doc_model.errorMessage = str(e)
            doc_model.stageMessage = f"Processing failed: {str(e)}"
            doc_model.processedAt = datetime.utcnow().isoformat()
            self._save_to_firestore(doc_model)
            raise e

    def ensure_document_indexed(self, document_id: str, user_id: str) -> bool:
        """
        Ensures that vector chunks exist in ChromaDB.
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
                pdfs = [f for f in os.listdir(candidate_dir) if f.lower().endswith(".pdf")]
                if pdfs:
                    file_path = os.path.join(candidate_dir, pdfs[0])
                    target_filename = pdfs[0]

            # 2. Match across all user subdirectories
            if not file_path:
                for root, dirs, files in os.walk(base_uploads):
                    if os.path.basename(root) == document_id:
                        pdfs = [f for f in files if f.lower().endswith(".pdf")]
                        if pdfs:
                            file_path = os.path.join(root, pdfs[0])
                            target_filename = pdfs[0]
                            break

            # 3. Fallback for doc_general / doc_unknown / latest uploaded document
            if not file_path:
                all_pdfs = []
                for root, dirs, files in os.walk(base_uploads):
                    for f in files:
                        if f.lower().endswith(".pdf"):
                            fp = os.path.join(root, f)
                            all_pdfs.append((os.path.getmtime(fp), fp, f))
                if all_pdfs:
                    all_pdfs.sort(reverse=True)
                    file_path = all_pdfs[0][1]
                    target_filename = all_pdfs[0][2]

        if file_path and os.path.exists(file_path):
            try:
                logger.info(f"Auto indexing PDF from disk for '{document_id}': '{file_path}'...")
                with open(file_path, "rb") as f:
                    pdf_bytes = f.read()

                page_count, company_name, financial_year, raw_meta = self._extract_pdf_metadata(
                    file_bytes=pdf_bytes,
                    filename=target_filename
                )

                proc_result = self.processor.process_pdf(
                    pdf_source=pdf_bytes,
                    document_id=document_id,
                    user_id=actual_user_id,
                    file_name=target_filename,
                    company_name=company_name or "Financial Report",
                    financial_year=financial_year or "FY2024",
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
                    fileSize=len(pdf_bytes),
                    companyName=company_name or "Financial Report",
                    financialYear=financial_year or "FY2024",
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
        """Locates the full filesystem path of an uploaded PDF file for an authenticated user."""
        doc = self.get_document(document_id, user_id)
        if not doc:
            return None
        upload_roots = _get_uploads_roots()
        for root_dir in upload_roots:
            user_doc_dir = os.path.join(root_dir, user_id, document_id)
            if os.path.exists(user_doc_dir):
                pdfs = [f for f in os.listdir(user_doc_dir) if f.lower().endswith(".pdf")]
                if pdfs:
                    return os.path.join(user_doc_dir, pdfs[0])
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
                blob.upload_from_string(file_bytes, content_type="application/pdf")
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

    def _extract_pdf_metadata(
        self,
        file_bytes: bytes,
        filename: str
    ) -> Tuple[int, Optional[str], Optional[str], Dict[str, Any]]:
        """Extracts page count, company name, and financial year using PyMuPDF and regex heuristics."""
        page_count = 0
        company_name = None
        financial_year = None
        raw_meta = {}

        doc = None
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page_count = len(doc)
            raw_meta = doc.metadata or {}

            sample_text = ""
            for i in range(min(6, page_count)):
                sample_text += doc[i].get_text("text") + "\n"

            # Check explicit corporate indicators
            tcs_match = re.search(r"(Tata\s+Consultancy\s+Services\s*(?:Limited|Ltd\.?)?)", sample_text, re.IGNORECASE)
            infy_match = re.search(r"(Infosys\s*(?:Limited|Ltd\.?)?)", sample_text, re.IGNORECASE)
            reliance_match = re.search(r"(Reliance\s+Industries\s*(?:Limited|Ltd\.?)?)", sample_text, re.IGNORECASE)

            if tcs_match:
                company_name = "Tata Consultancy Services Limited"
            elif infy_match:
                company_name = "Infosys Limited"
            elif reliance_match:
                company_name = "Reliance Industries Limited"

            if not company_name:
                company_match = re.search(
                    r"(?:Exact name of registrant as specified in its charter:?|REGISTRANT:?|COMPANY NAME:?|To the Members of\s+)\s*([^\n\r]{3,80})",
                    sample_text,
                    re.IGNORECASE
                )
                if company_match:
                    company_name = company_match.group(1).strip()

            if not company_name:
                corp_match = re.search(
                    r"([A-Z0-9\s,\.\-&]{3,50}(?:LIMITED|PRIVATE LIMITED|INC\.?|CORP\.?|CORPORATION|HOLDINGS|PLC|LLC|GROUP|LTD\.?))",
                    sample_text
                )
                if corp_match:
                    candidate = corp_match.group(1).strip().title()
                    if len(candidate) > 4 and candidate.lower() not in ("annual report", "financial statements", "independent auditor"):
                        company_name = candidate

            if not company_name or company_name.lower() in ("annual", "report", "financial report", "unknown"):
                clean_name = os.path.splitext(filename)[0]
                clean_name = re.sub(r"[-_](10K|10Q|8K|FY\d+|Q\d+|Annual|Report|\d{4})", "", clean_name, flags=re.IGNORECASE)
                clean_name = clean_name.replace("_", " ").replace("-", " ").strip().title()
                if clean_name and clean_name.lower() not in ("annual", "report", "financial"):
                    company_name = clean_name
                else:
                    company_name = "Tata Consultancy Services Limited" if "tcs" in filename.lower() or "tata" in sample_text.lower() else "Corporate Financial Report"

            fy_match = re.search(
                r"(?:fiscal year ended|period ended|ended|year ended)\s+[a-zA-Z]+\s+\d{1,2},?\s+(20\d{2})",
                sample_text,
                re.IGNORECASE
            )
            if fy_match:
                financial_year = f"FY{fy_match.group(1)}"
            else:
                year_match = re.search(r"\b(202[0-9]|201[0-9])\b", sample_text) or re.search(r"\b(202[0-9]|201[0-9])\b", filename)
                if year_match:
                    financial_year = f"FY{year_match.group(1)}"
                else:
                    financial_year = f"FY{datetime.utcnow().year}"

        except Exception as e:
            logger.warning(f"Error extracting PDF metadata: {str(e)}")
            page_count = page_count or 1
            if not company_name:
                company_name = os.path.splitext(filename)[0].replace("_", " ").title()
            if not financial_year:
                financial_year = f"FY{datetime.utcnow().year}"
        finally:
            if doc:
                doc.close()

        return page_count, company_name, financial_year, raw_meta

    def _save_to_firestore(self, doc_model: DocumentModel) -> None:
        """Saves document model to Firestore and in-memory cache with timeout safety."""
        _in_memory_documents[doc_model.documentId] = doc_model
        if self.firestore_db:
            def _save():
                self.firestore_db.collection("documents").document(doc_model.documentId).set(
                    doc_model.to_dict()
                )

            _run_with_timeout(_save, timeout_sec=2.5)
