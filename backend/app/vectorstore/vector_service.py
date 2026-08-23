import os
from typing import List, Dict, Any, Optional

# Disable ChromaDB telemetry for faster startup
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.config import Settings as ChromaSettings

from .embeddings import get_embedding_function
from ..document_processing.chunker import DocumentChunk
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

_chroma_client: Optional[chromadb.PersistentClient] = None
COLLECTION_NAME = "financial_reports_chunks"


def get_chroma_client() -> chromadb.PersistentClient:
    """Initializes and returns the singleton persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

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
    Enforces strict user-level document isolation and duplicate prevention.
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
        Checks if vector chunks for a specific document and user already exist.
        """
        try:
            results = self.collection.get(
                where={"$and": [{"document_id": document_id}, {"user_id": user_id}]},
                limit=1
            )
            return bool(results and results.get("ids") and len(results["ids"]) > 0)
        except Exception as e:
            logger.debug(f"document_exists check note: {str(e)}")
            return False

    def add_document(
        self,
        document_id: str,
        user_id: str,
        chunks: List[DocumentChunk],
        overwrite_if_exists: bool = True
    ) -> int:
        """
        Embeds document chunks using Sentence Transformers and stores them in ChromaDB.
        Prevents duplicate ingestion by overwriting existing chunks if present.
        """
        if not chunks:
            logger.warning(f"add_document called with 0 chunks for document '{document_id}'.")
            return 0

        # Avoid duplicate ingestion
        if self.document_exists(document_id, user_id):
            if overwrite_if_exists:
                logger.info(f"Document '{document_id}' exists for user '{user_id}'. Overwriting existing vectors...")
                self.delete_document(document_id, user_id)
            else:
                logger.info(f"Document '{document_id}' already indexed for user '{user_id}'. Skipping addition.")
                return 0

        # Generate embeddings using Sentence Transformers
        embedder = get_embedding_function()
        texts = [chunk.text for chunk in chunks]
        embeddings = embedder.encode(texts, show_progress_bar=False).tolist()

        ids: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        documents: List[str] = []

        for idx, chunk in enumerate(chunks):
            c_id = chunk.chunk_id or f"{document_id}_p{chunk.page_number}_c{idx}"
            ids.append(c_id)
            documents.append(chunk.text)

            meta = dict(chunk.metadata) if hasattr(chunk, "metadata") and chunk.metadata else {}
            meta["document_id"] = document_id
            meta["user_id"] = user_id
            meta["page_number"] = getattr(chunk, "page_number", 1)
            meta["section"] = str(getattr(chunk, "section", "General"))
            meta["file_name"] = str(meta.get("file_name", "document.pdf"))
            meta["company_name"] = str(meta.get("company_name", "Unknown"))
            meta["financial_year"] = str(meta.get("financial_year", "FY2024"))
            metadatas.append(meta)

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        logger.info(f"Added {len(chunks)} vector chunks for document '{document_id}' (User: '{user_id}').")
        return len(chunks)

    def search(
        self,
        query_text: str,
        user_id: str,
        document_id: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic vector search matching query_text.
        STRICT SECURITY ENFORCEMENT: Always filters by user_id so chunks from other users are NEVER returned.
        """
        if not query_text or not user_id:
            return []

        settings = get_settings()
        k = top_k or settings.DEFAULT_TOP_K

        # Mandatory user isolation filter
        if document_id:
            where_filter: Dict[str, Any] = {
                "$and": [
                    {"user_id": user_id},
                    {"document_id": document_id}
                ]
            }
        else:
            where_filter = {"user_id": user_id}

        embedder = get_embedding_function()
        query_vector = embedder.encode([query_text]).tolist()

        results = self.collection.query(
            query_embeddings=query_vector,
            n_results=k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        formatted: List[Dict[str, Any]] = []

        if results and results.get("documents") and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
            ids = results["ids"][0] if results.get("ids") else [""] * len(docs)

            for doc, meta, dist, chunk_id in zip(docs, metas, dists, ids):
                # Cosine distance to similarity conversion
                similarity = round(max(0.0, 1.0 - float(dist)), 4) if dist is not None else 1.0

                formatted.append({
                    "chunk_id": chunk_id,
                    "text": doc,
                    "similarity_score": similarity,
                    "page_number": meta.get("page_number", 1),
                    "section": meta.get("section", "General"),
                    "document_id": meta.get("document_id", document_id or ""),
                    "user_id": meta.get("user_id", user_id),
                    "file_name": meta.get("file_name", ""),
                    "company_name": meta.get("company_name", ""),
                    "financial_year": meta.get("financial_year", ""),
                    "metadata": meta
                })

        return formatted

    def delete_document(self, document_id: str, user_id: str) -> bool:
        """
        Deletes all vector chunks associated with a specific document_id and user_id.
        """
        try:
            self.collection.delete(
                where={"$and": [{"document_id": document_id}, {"user_id": user_id}]}
            )
            logger.info(f"Deleted vector chunks for document '{document_id}' (User: '{user_id}').")
            return True
        except Exception as e:
            logger.warning(f"Error deleting chunks for document '{document_id}': {str(e)}")
            try:
                self.collection.delete(where={"document_id": document_id})
                return True
            except Exception as ex:
                logger.error(f"Fallback delete failed for '{document_id}': {str(ex)}")
                return False

    # Backward compatibility aliases
    def upsert_chunks(self, chunks: List[DocumentChunk]) -> int:
        if not chunks:
            return 0
        doc_id = chunks[0].metadata.get("document_id") or getattr(chunks[0], "report_id", "doc_unknown")
        user_id = chunks[0].user_id
        return self.add_document(document_id=doc_id, user_id=user_id, chunks=chunks)

    def query_similar_chunks(
        self,
        query_text: str,
        report_id: str,
        user_id: Optional[str] = None,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        return self.search(
            query_text=query_text,
            user_id=user_id or "default_user",
            document_id=report_id,
            top_k=top_k
        )

    def delete_report_chunks(self, report_id: str) -> None:
        self.delete_document(document_id=report_id, user_id="default_user")


# Backward compatibility alias
ChromaVectorService = VectorStoreService
