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


class DocumentService:
    """Service handling document upload, storage, metadata extraction, chunking, vector indexing, and Firestore CRUD."""

    def __init__(self):
        self.firestore_db = get_firestore_client()
        self.storage_bucket = get_storage_bucket()
        self.settings = get_settings()
        self.processor = DocumentProcessor()
        self.vector_service = VectorStoreService()

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
        document_id = f"doc_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.utcnow().isoformat()

        # Step 1: Create initial record with 'uploaded' status
        doc_model = DocumentModel(
            documentId=document_id,
            userId=user_id,
            fileName=filename,
            fileSize=len(file_bytes),
            status="uploaded",
            uploadedAt=now_iso,
            storageUrl=""
        )
        self._save_to_firestore(doc_model)

        try:
            # Step 2: Update status to 'processing'
            doc_model.status = "processing"
            self._save_to_firestore(doc_model)

            # Step 3: Store file (Firebase Storage or local uploads directory)
            storage_url = self._store_file(
                file_bytes=file_bytes,
                filename=filename,
                user_id=user_id,
                document_id=document_id
            )
            doc_model.storageUrl = storage_url

            # Step 4: Extract metadata from PDF bytes
            page_count, company_name, financial_year, raw_meta = self._extract_pdf_metadata(
                file_bytes=file_bytes,
                filename=filename
            )

            doc_model.pageCount = page_count
            doc_model.companyName = company_name
            doc_model.financialYear = financial_year
            doc_model.metadata = raw_meta

            # Step 5: Execute complete PDF processing pipeline & ChromaDB vector indexing
            logger.info(f"Running DocumentProcessor pipeline for '{filename}' ({document_id})...")
            proc_result = self.processor.process_pdf(
                pdf_source=file_bytes,
                document_id=document_id,
                user_id=user_id,
                file_name=filename,
                company_name=company_name,
                financial_year=financial_year,
            )

            # Index chunks into ChromaDB
            indexed_count = self.vector_service.add_document(
                document_id=document_id,
                user_id=user_id,
                chunks=proc_result.chunks,
                overwrite_if_exists=True
            )

            doc_model.status = "completed"
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
            doc_model.errorMessage = str(e)
            doc_model.processedAt = datetime.utcnow().isoformat()
            self._save_to_firestore(doc_model)
            raise e

    def ensure_document_indexed(self, document_id: str, user_id: str) -> bool:
        """
        Ensures that vector chunks exist in ChromaDB for the given document_id.
        If chunks do not exist yet (e.g. uploaded previously), re-indexes from stored file.
        """
        if self.vector_service.document_exists(document_id=document_id, user_id=user_id):
            return True

        doc_model = self.get_document(document_id, user_id)
        if not doc_model:
            for doc in _in_memory_documents.values():
                if doc.documentId == document_id:
                    doc_model = doc
                    break

        if not doc_model:
            return False

        file_path = None
        upload_dir = os.path.join(os.getcwd(), "uploads", doc_model.userId, document_id)
        if os.path.exists(upload_dir):
            files = os.listdir(upload_dir)
            if files:
                file_path = os.path.join(upload_dir, files[0])

        if not file_path or not os.path.exists(file_path):
            base_uploads = os.path.join(os.getcwd(), "uploads")
            if os.path.exists(base_uploads):
                for root, dirs, files in os.walk(base_uploads):
                    if document_id in root or (files and any(f.lower().endswith('.pdf') for f in files)):
                        for f in files:
                            if f.lower().endswith('.pdf'):
                                file_path = os.path.join(root, f)
                                break

        if file_path and os.path.exists(file_path):
            try:
                logger.info(f"Auto re-indexing PDF from disk for '{document_id}': '{file_path}'...")
                with open(file_path, "rb") as f:
                    pdf_bytes = f.read()

                proc_result = self.processor.process_pdf(
                    pdf_source=pdf_bytes,
                    document_id=document_id,
                    user_id=user_id or doc_model.userId,
                    file_name=doc_model.fileName,
                    company_name=doc_model.companyName,
                    financial_year=doc_model.financialYear,
                )

                self.vector_service.add_document(
                    document_id=document_id,
                    user_id=user_id or doc_model.userId,
                    chunks=proc_result.chunks,
                    overwrite_if_exists=True
                )
                return True
            except Exception as e:
                logger.error(f"Failed auto re-indexing document {document_id}: {str(e)}")
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
        """Deletes a document record, vector chunks, and storage file."""
        if self.firestore_db:
            def _del():
                self.firestore_db.collection("documents").document(document_id).delete()

            _run_with_timeout(_del, timeout_sec=2.5)

        if document_id in _in_memory_documents:
            del _in_memory_documents[document_id]

        self.vector_service.delete_document(document_id=document_id, user_id=user_id)
        return True

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
            for i in range(min(3, page_count)):
                sample_text += doc[i].get_text("text") + "\n"

            company_match = re.search(
                r"(?:Exact name of registrant as specified in its charter:?|REGISTRANT:?|COMPANY NAME:?)\s*([^\n\r]{3,80})",
                sample_text,
                re.IGNORECASE
            )
            if company_match:
                company_name = company_match.group(1).strip()

            if not company_name:
                corp_match = re.search(
                    r"([A-Z0-9\s,\.\-&]{3,50}(?:INC\.?|CORP\.?|CORPORATION|HOLDINGS|PLC|LLC|GROUP|LTD\.?))",
                    sample_text
                )
                if corp_match:
                    company_name = corp_match.group(1).strip().title()

            if not company_name or len(company_name) < 2:
                clean_name = os.path.splitext(filename)[0]
                clean_name = re.sub(r"[-_](10K|10Q|8K|FY\d+|Q\d+|Annual|Report|\d{4})", "", clean_name, flags=re.IGNORECASE)
                company_name = clean_name.replace("_", " ").replace("-", " ").strip().title()

            fy_match = re.search(
                r"(?:fiscal year ended|period ended|ended)\s+[a-zA-Z]+\s+\d{1,2},?\s+(20\d{2})",
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
