import os
from typing import List, Dict, Any, Optional

# Disable ChromaDB telemetry to avoid startup network latency
import gc

# Disable ChromaDB telemetry to avoid startup network latency
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from .embeddings import get_embedding_function
from ..document_processing.chunker import DocumentChunk
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

_chroma_client = None
COLLECTION_NAME = "financial_reports_chunks"


def get_chroma_client():
    """Returns persistent ChromaDB client, lazy-loaded on first vector query."""
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
    logger.info(f"Initialized ChromaDB persistent client at: {persist_dir}")
    return _chroma_client


def reset_chroma_client():
    """Force-resets the global ChromaDB client (used after ephemeral storage restart)."""
    global _chroma_client
    _chroma_client = None
    logger.warning("ChromaDB client reset. It will be re-initialized on next access.")


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



class ChromaVectorService:
    """Service handling vector storage and semantic retrieval."""

    def __init__(self):
        self._collection = None

    @property
    def collection(self):
        """Lazy loads ChromaDB collection on first access. Re-initializes if the
        client was reset due to ephemeral storage restart (e.g. on Render free tier)."""
        if self._collection is None:
            client = get_chroma_client()
            self._collection = client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
        else:
            # Sanity-check: if the underlying client was evicted (e.g. OOM / restart),
            # the stored _collection object becomes stale. Detect this and re-create.
            try:
                _ = self._collection.count()  # lightweight no-op ping
            except Exception:
                logger.warning(
                    "ChromaDB collection ping failed — likely ephemeral storage restart. "
                    "Re-initializing client and collection..."
                )
                reset_chroma_client()
                self._collection = None
                client = get_chroma_client()
                self._collection = client.get_or_create_collection(
                    name=COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"}
                )
        return self._collection

    def upsert_chunks(self, chunks: List[DocumentChunk]) -> int:
        """Embeds and upserts document chunks into ChromaDB."""
        if not chunks:
            return 0

        embedder = get_embedding_function()
        texts = [chunk.text for chunk in chunks]
        raw_embeddings = embedder.encode(texts, show_progress_bar=False)
        embeddings = _safe_to_list(raw_embeddings)

        ids = [chunk.chunk_id for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        documents = texts

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Successfully upserted {len(chunks)} chunks into ChromaDB.")
        return len(chunks)

    def query_similar_chunks(
        self,
        query_text: str,
        report_id: str,
        user_id: Optional[str] = None,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """Queries the vector store for most relevant chunks matching query_text."""
        embedder = get_embedding_function()
        raw_query_vector = embedder.encode([query_text])
        query_vector = _safe_to_list(raw_query_vector)

        where_filter: Dict[str, Any] = {"report_id": report_id}
        if user_id:
            where_filter = {
                "$and": [
                    {"report_id": report_id},
                    {"user_id": user_id}
                ]
            }

        results = self.collection.query(
            query_embeddings=query_vector,
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        formatted_chunks = []
        if results and results.get("documents") and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
            ids = results["ids"][0] if results.get("ids") else [""] * len(docs)

            for doc, meta, dist, chunk_id in zip(docs, metas, dists, ids):
                formatted_chunks.append({
                    "chunk_id": chunk_id,
                    "text": doc,
                    "page_number": meta.get("page_number", 1),
                    "similarity_score": round(1.0 - dist, 4) if dist is not None else 1.0,
                    "metadata": meta
                })

        return formatted_chunks

    def delete_report_chunks(self, report_id: str) -> None:
        """Deletes all chunks associated with a specific report."""
        try:
            self.collection.delete(where={"report_id": report_id})
            logger.info(f"Deleted vector chunks for report_id: {report_id}")
        except Exception as e:
            logger.warning(f"Error deleting chunks for report_id {report_id}: {str(e)}")
