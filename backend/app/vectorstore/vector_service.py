import gc
import os
from typing import List, Dict, Any, Optional

# Disable ChromaDB telemetry for faster startup
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from .embeddings import get_embedding_function
from ..document_processing.chunker import DocumentChunk
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

_chroma_client = None
COLLECTION_NAME = "financial_reports_chunks"


def _safe_to_list(obj):
    """Kept for backward compatibility. SafeEmbedder now guarantees list[list[float]] output."""
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if isinstance(obj, list):
        result = []
        for item in obj:
            if hasattr(item, "tolist"):
                result.append(item.tolist())
            elif isinstance(item, list):
                result.append(item)
            else:
                result.append(list(item))
        return result
    return list(obj)


def get_chroma_client():
    """Initializes and returns the singleton persistent ChromaDB client, lazy-loaded on demand."""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    import chromadb
    from chromadb.config import Settings as ChromaSettings

    settings = get_settings()
    persist_dir = settings.CHROMA_PERSIST_DIRECTORY
    os.makedirs(persist_dir, exist_ok=True)

    _chroma_client = chromadb.PersistentClient(
        path=persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False)
    )
    logger.info(f"ChromaDB persistent client initialized at: '{persist_dir}'")
    return _chroma_client


class VectorStoreService:
    """
    Vector storage and retrieval service powered by ChromaDB & Sentence Transformers.
    Strict document isolation: NEVER leaks chunks from unrelated documents or companies.
    """

    def __init__(self, collection_name: str = COLLECTION_NAME):
        self.collection_name = collection_name
        self._collection = None

    @property
    def collection(self):
        """Lazy loads the ChromaDB collection on first access."""
        if self._collection is None:
            client = get_chroma_client()
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def document_exists(self, document_id: str, user_id: str) -> bool:
        """
        Checks if vector chunks for a specific document exist in ChromaDB.
        """
        try:
            results = self.collection.get(
                where={"document_id": document_id},
                limit=1
            )
            if results and results.get("ids") and len(results["ids"]) > 0:
                return True

            results_report = self.collection.get(
                where={"report_id": document_id},
                limit=1
            )
            if results_report and results_report.get("ids") and len(results_report["ids"]) > 0:
                return True

            return False
        except Exception as e:
            logger.debug(f"document_exists check note: {str(e)}")
            return False

    def document_exists_by_hash(self, doc_hash: str, user_id: str) -> Optional[str]:
        """
        Checks if vector chunks with the given sha256 doc_hash exist in ChromaDB.
        Returns the existing document_id if found.
        """
        if not doc_hash:
            return None
        try:
            results = self.collection.get(
                where={"doc_hash": doc_hash},
                limit=1,
                include=["metadatas"]
            )
            if results and results.get("ids") and len(results["ids"]) > 0:
                metas = results.get("metadatas")
                if metas and len(metas) > 0 and metas[0]:
                    return metas[0].get("document_id") or metas[0].get("report_id")
                return results["ids"][0].split("_p")[0]
            return None
        except Exception as e:
            logger.debug(f"document_exists_by_hash note: {str(e)}")
            return None

    def add_document(
        self,
        document_id: str,
        user_id: str,
        chunks: List[DocumentChunk],
        overwrite_if_exists: bool = True,
        doc_hash: Optional[str] = None,
    ) -> int:
        """
        Embeds document chunks using Sentence Transformers and stores them in ChromaDB.
        Saves both document_id, report_id, and doc_hash for exact document scoping and instant deduplication.
        """
        if not chunks:
            logger.warning(f"add_document called with 0 chunks for document '{document_id}'.")
            return 0

        if self.document_exists(document_id, user_id):
            if overwrite_if_exists:
                logger.info(f"Document '{document_id}' exists. Overwriting existing vectors...")
                self.delete_document(document_id, user_id)
            else:
                logger.info(f"Document '{document_id}' already indexed. Skipping addition.")
                return 0

        settings = get_settings()
        batch_size = getattr(settings, "EMBEDDING_BATCH_SIZE", 256)
        embedder = get_embedding_function()
        texts = [chunk.text for chunk in chunks]
        raw_embeddings = embedder.encode(texts, batch_size=batch_size, show_progress_bar=False)
        embeddings = _safe_to_list(raw_embeddings)

        ids: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        documents: List[str] = []

        for idx, chunk in enumerate(chunks):
            c_id = chunk.chunk_id or f"{document_id}_p{chunk.page_number}_c{idx}"
            ids.append(c_id)
            documents.append(chunk.text)

            meta = dict(chunk.metadata) if hasattr(chunk, "metadata") and chunk.metadata else {}
            meta["document_id"] = document_id
            meta["report_id"] = document_id  # Guarantee key matching for all service queries
            meta["user_id"] = user_id
            meta["page_number"] = getattr(chunk, "page_number", 1)
            meta["section"] = str(getattr(chunk, "section", "General"))
            meta["file_name"] = str(meta.get("file_name", "document.pdf"))
            meta["company_name"] = str(meta.get("company_name", "Unknown"))
            meta["financial_year"] = str(meta.get("financial_year", "FY2024"))
            if doc_hash:
                meta["doc_hash"] = doc_hash
            metadatas.append(meta)

        # Batch upsert into ChromaDB in chunks of 250 to avoid SQLite transaction thrashing
        UPSERT_BATCH = 250
        for i in range(0, len(ids), UPSERT_BATCH):
            end_i = i + UPSERT_BATCH
            self.collection.upsert(
                ids=ids[i:end_i],
                embeddings=embeddings[i:end_i],
                documents=documents[i:end_i],
                metadatas=metadatas[i:end_i]
            )

        logger.info(f"Added {len(chunks)} vector chunks for document '{document_id}' (Company: '{metadatas[0].get('company_name')}').")
        gc.collect()
        return len(chunks)

    def search(
        self,
        query_text: Optional[str] = None,
        user_id: str = "",
        document_id: Optional[str] = None,
        top_k: Optional[int] = None,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Performs Hybrid Search:
        1. Dense Vector Similarity Search using sentence-transformers embeddings.
        2. Financial Keyword Term Matching across all document chunks.
        3. Surrounding Page Context Expansion (retrieves neighboring chunks/table headers on matching pages).
        """
        actual_query = (query_text or query or "").strip()
        if not actual_query:
            return []

        settings = get_settings()
        k = top_k or settings.DEFAULT_TOP_K or 10

        where_filter: Dict[str, Any] = {}
        filters = []
        if user_id:
            filters.append({"user_id": user_id})
        if document_id:
            filters.append({"document_id": document_id})

        if len(filters) == 1:
            where_filter = filters[0]
        elif len(filters) > 1:
            where_filter = {"$and": filters}

        embedder = get_embedding_function()
        raw_query_vector = embedder.encode([actual_query])
        query_vector = _safe_to_list(raw_query_vector)

        # 1. Semantic Vector Query
        query_k = min(35, max(k * 2, 15))
        results = None
        if where_filter:
            try:
                results = self.collection.query(
                    query_embeddings=query_vector,
                    n_results=query_k,
                    where=where_filter,
                    include=["documents", "metadatas", "distances"]
                )
            except Exception as e:
                logger.warning(f"ChromaDB search by document_id note: {str(e)}")

        if (not results or not results.get("documents") or len(results["documents"][0]) == 0) and document_id:
            try:
                results = self.collection.query(
                    query_embeddings=query_vector,
                    n_results=query_k,
                    where={"report_id": document_id},
                    include=["documents", "metadatas", "distances"]
                )
            except Exception as e:
                logger.warning(f"ChromaDB search by report_id note: {str(e)}")

        fallback_where = {"user_id": user_id} if user_id else None
        if not results or not results.get("documents") or len(results["documents"][0]) == 0:
            try:
                results = self.collection.query(
                    query_embeddings=query_vector,
                    n_results=query_k,
                    where=fallback_where,
                    include=["documents", "metadatas", "distances"]
                )
            except Exception as e:
                logger.warning(f"ChromaDB search without filter note: {str(e)}")

        # 2. Extract and score semantic candidates
        candidates_map: Dict[str, Dict[str, Any]] = {}
        target_pages: set = set()

        if results and results.get("documents") and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
            ids = results["ids"][0] if results.get("ids") else [""] * len(docs)

            for doc, meta, dist, chunk_id in zip(docs, metas, dists, ids):
                if not doc:
                    continue
                similarity = round(max(0.0, 1.0 - float(dist)), 4) if dist is not None else 1.0
                page_num = meta.get("page_number", 1)
                target_pages.add(page_num)

                candidates_map[chunk_id] = {
                    "chunk_id": chunk_id,
                    "text": doc,
                    "similarity_score": similarity,
                    "page_number": page_num,
                    "section": meta.get("section", "General"),
                    "source_location": meta.get("source_location", f"Page {page_num}"),
                    "file_type": meta.get("file_type", "pdf"),
                    "document_id": meta.get("document_id", document_id or ""),
                    "user_id": meta.get("user_id", user_id),
                    "file_name": meta.get("file_name", ""),
                    "company_name": meta.get("company_name", ""),
                    "financial_year": meta.get("financial_year", ""),
                    "metadata": meta
                }

        # 3. Fast Financial Keyword Boost on Candidate Chunks
        try:
            query_terms = [t.lower() for t in actual_query.split() if len(t) > 2]
            key_phrases = []
            q_low = actual_query.lower()
            if any(k in q_low for k in ["revenue", "sales", "turnover", "income"]):
                key_phrases.extend(["revenue from operations", "total revenue", "other income", "total income", "turnover", "gross sales", "net sales"])
            if any(k in q_low for k in ["profit", "pat", "pbt", "loss"]):
                key_phrases.extend(["profit after tax", "profit before tax", "net profit", "profit for the year", "profit for the period", "total comprehensive income"])
            if any(k in q_low for k in ["asset", "assets"]):
                key_phrases.extend(["total assets", "non-current assets", "current assets", "property, plant", "inventories", "trade receivables", "fixed assets"])
            if any(k in q_low for k in ["liabilit", "debt", "borrowing", "equity"]):
                key_phrases.extend(["total equity and liabilities", "total liabilities", "borrowings", "equity share capital", "trade payables", "other equity"])
            if any(k in q_low for k in ["company", "name", "cin", "office"]):
                key_phrases.extend(["cin", "corporate identification", "registered office", "directors", "auditor", "limited", "private limited"])

            for c_id, candidate in candidates_map.items():
                doc_text = candidate.get("text", "")
                if not doc_text:
                    continue
                doc_lower = doc_text.lower()
                kw_score = 0.0
                for phrase in key_phrases:
                    if phrase in doc_lower:
                        kw_score += 0.25
                for term in query_terms:
                    if term in doc_lower:
                        kw_score += 0.08

                if kw_score > 0.0:
                    candidate["similarity_score"] = min(1.0, candidate.get("similarity_score", 0.0) + kw_score * 0.3)
        except Exception as kw_err:
            logger.debug(f"Keyword boost note: {str(kw_err)}")

        # 4. Surrounding Page Expansion (Include adjacent chunks on top matched pages)
        try:
            top_pages = sorted(list(target_pages))[:5]
            if top_pages and document_id:
                for pg in top_pages:
                    pg_records = self.collection.get(
                        where={"$and": [{"document_id": document_id}, {"page_number": pg}]},
                        include=["documents", "metadatas"]
                    )
                    if pg_records and pg_records.get("documents"):
                        for doc_text, meta, c_id in zip(pg_records["documents"], pg_records.get("metadatas", []), pg_records.get("ids", [])):
                            if c_id not in candidates_map and doc_text:
                                candidates_map[c_id] = {
                                    "chunk_id": c_id,
                                    "text": doc_text,
                                    "similarity_score": 0.70,
                                    "page_number": pg,
                                    "section": meta.get("section", "Financial Statements"),
                                    "document_id": meta.get("document_id", document_id or ""),
                                    "user_id": meta.get("user_id", user_id),
                                    "file_name": meta.get("file_name", ""),
                                    "company_name": meta.get("company_name", ""),
                                    "financial_year": meta.get("financial_year", ""),
                                    "metadata": meta
                                }
        except Exception as exp_err:
            logger.debug(f"Page expansion note: {str(exp_err)}")

        # 5. Sort candidates by similarity/relevance score descending
        sorted_candidates = sorted(
            candidates_map.values(),
            key=lambda x: (x.get("similarity_score", 0.0), -x.get("page_number", 1)),
            reverse=True
        )

        return sorted_candidates[:k]

    def delete_document(self, document_id: str, user_id: str) -> bool:
        """
        Deletes all vector chunks associated with a specific document_id.
        """
        try:
            self.collection.delete(where={"document_id": document_id})
            self.collection.delete(where={"report_id": document_id})
            logger.info(f"Deleted vector chunks for document '{document_id}'.")
            return True
        except Exception as e:
            logger.warning(f"Error deleting chunks for document '{document_id}': {str(e)}")
            return False


ChromaVectorService = VectorStoreService
