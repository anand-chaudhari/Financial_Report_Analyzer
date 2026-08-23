import os
import re
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from ..models.document_model import DocumentModel
from ..firebase.firestore import get_firestore_client
from ..firebase.storage import get_storage_bucket
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# In-memory storage fallback for local development
_in_memory_documents: Dict[str, DocumentModel] = {}


class DocumentService:
    """Service handling document upload, storage, metadata extraction, and Firestore CRUD."""

    def __init__(self):
        self.firestore_db = get_firestore_client()
        self.storage_bucket = get_storage_bucket()
        self.settings = get_settings()

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
        4. Saves document record to Firestore with status 'completed'
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
            doc_model.status = "completed"
            doc_model.processedAt = datetime.utcnow().isoformat()

            # Step 5: Save final completed record to Firestore
            self._save_to_firestore(doc_model)
            logger.info(
                f"Document '{filename}' (ID: {document_id}) processed successfully: "
                f"{page_count} pages, Company: '{company_name}', Year: '{financial_year}'"
            )
            return doc_model

        except Exception as e:
            logger.error(f"Failed processing document upload {document_id}: {str(e)}", exc_info=True)
            doc_model.status = "failed"
            doc_model.errorMessage = str(e)
            doc_model.processedAt = datetime.utcnow().isoformat()
            self._save_to_firestore(doc_model)
            raise e

    def get_document(self, document_id: str, user_id: str) -> Optional[DocumentModel]:
        """Retrieves a document record for the authenticated user."""
        if self.firestore_db:
            try:
                doc = self.firestore_db.collection("documents").document(document_id).get()
                if doc.exists:
                    data = doc.to_dict()
                    if data.get("userId") == user_id:
                        return DocumentModel.from_dict(data)
            except Exception as e:
                logger.error(f"Firestore get_document error: {str(e)}")

        doc_local = _in_memory_documents.get(document_id)
        if doc_local and doc_local.userId == user_id:
            return doc_local
        return None

    def list_user_documents(self, user_id: str) -> List[DocumentModel]:
        """Lists all document records belonging to the authenticated user."""
        if self.firestore_db:
            try:
                docs = (
                    self.firestore_db.collection("documents")
                    .where("userId", "==", user_id)
                    .stream()
                )
                return [DocumentModel.from_dict(doc.to_dict()) for doc in docs]
            except Exception as e:
                logger.error(f"Firestore list_user_documents error: {str(e)}")

        return [d for d in _in_memory_documents.values() if d.userId == user_id]

    def delete_document(self, document_id: str, user_id: str) -> bool:
        """Deletes a document record and storage file."""
        if self.firestore_db:
            try:
                self.firestore_db.collection("documents").document(document_id).delete()
            except Exception as e:
                logger.error(f"Firestore delete document error: {str(e)}")

        if document_id in _in_memory_documents:
            del _in_memory_documents[document_id]

        return True

    def _store_file(
        self,
        file_bytes: bytes,
        filename: str,
        user_id: str,
        document_id: str
    ) -> str:
        """Saves file to Firebase Storage if available, else local storage."""
        # 1. Try Firebase Storage
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

        # 2. Local file storage fallback
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

            # Read text from first 3 pages
            sample_text = ""
            for i in range(min(3, page_count)):
                sample_text += doc[i].get_text("text") + "\n"

            # 1. Company Name Extraction Heuristics
            # Look for "Commission File Number" or standard 10-K headers
            company_match = re.search(
                r"(?:Exact name of registrant as specified in its charter:?|REGISTRANT:?|COMPANY NAME:?)\s*([^\n\r]{3,80})",
                sample_text,
                re.IGNORECASE
            )
            if company_match:
                company_name = company_match.group(1).strip()

            # Pattern for uppercase corporate names (e.g. APPLE INC., MICROSOFT CORPORATION, NVIDIA CORP)
            if not company_name:
                corp_match = re.search(
                    r"([A-Z0-9\s,\.\-&]{3,50}(?:INC\.?|CORP\.?|CORPORATION|HOLDINGS|PLC|LLC|GROUP|LTD\.?))",
                    sample_text
                )
                if corp_match:
                    company_name = corp_match.group(1).strip().title()

            # Fallback company from filename
            if not company_name or len(company_name) < 2:
                clean_name = os.path.splitext(filename)[0]
                clean_name = re.sub(r"[-_](10K|10Q|8K|FY\d+|Q\d+|Annual|Report|\d{4})", "", clean_name, flags=re.IGNORECASE)
                company_name = clean_name.replace("_", " ").replace("-", " ").strip().title()

            # 2. Financial Year Extraction Heuristics
            # Look for "For the fiscal year ended [Date] [Year]"
            fy_match = re.search(
                r"(?:fiscal year ended|period ended|ended)\s+[a-zA-Z]+\s+\d{1,2},?\s+(20\d{2})",
                sample_text,
                re.IGNORECASE
            )
            if fy_match:
                financial_year = f"FY{fy_match.group(1)}"
            else:
                # Look for FY2024, FY24, or 2024 in text or filename
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
        """Saves document model to Firestore and in-memory cache."""
        _in_memory_documents[doc_model.documentId] = doc_model
        if self.firestore_db:
            try:
                self.firestore_db.collection("documents").document(doc_model.documentId).set(
                    doc_model.to_dict()
                )
            except Exception as e:
                logger.error(f"Firestore document set error: {str(e)}")
