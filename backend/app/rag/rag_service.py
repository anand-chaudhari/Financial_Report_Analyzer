import re
from typing import List, Dict, Any, Optional
from ..vectorstore.vector_service import VectorStoreService
from ..llm.llm_client import GroqLLMClient
from .prompts import STRICT_RAG_SYSTEM_PROMPT, NO_INFORMATION_FALLBACK_RESPONSE
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class RAGService:
    """
    Complete Grounded RAG Question-Answering Engine.
    Architecture:
    User Question -> Query Embedding -> ChromaDB Retrieval -> Relevant Chunks
    -> Context Construction -> Groq LLM -> Grounded Answer -> Sources & Page Citations
    """

    def __init__(
        self,
        vector_service: Optional[VectorStoreService] = None,
        llm_client: Optional[GroqLLMClient] = None,
    ):
        self.vector_service = vector_service or VectorStoreService()
        self.llm_client = llm_client or GroqLLMClient()

    def validate_document_access(self, user_id: str, document_id: str) -> bool:
        """
        Validates document ownership and existence in ChromaDB vector store.
        """
        if not user_id or not document_id:
            return False
        return self.vector_service.document_exists(document_id=document_id, user_id=user_id)

    def _format_context(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        Constructs context text from retrieved chunks with page number and section metadata.
        """
        context_blocks = []
        for idx, chunk in enumerate(retrieved_chunks, 1):
            page_no = chunk.get("page_number", 1)
            sec = chunk.get("section") or "General Financial Content"
            text = chunk.get("text", "")
            context_blocks.append(f"--- Chunk {idx} [Page {page_no}] [Section: {sec}] ---\n{text}")
        return "\n\n".join(context_blocks)

    def _format_history(self, conversation_history: Optional[List[Dict[str, Any]]]) -> str:
        """Formats conversation history for prompt inclusion."""
        if not conversation_history:
            return "None"
        formatted = []
        for msg in conversation_history:
            role = msg.get("role") or msg.get("sender") or "User"
            content = msg.get("content") or msg.get("text") or ""
            if content:
                formatted.append(f"{role.capitalize()}: {content}")
        return "\n".join(formatted) if formatted else "None"

    def answer_question(
        self,
        user_id: str,
        document_id: str,
        question: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes full RAG query process:
        1. Validate ownership
        2. Vector search & filter by document_id and user_id
        3. Build context with page & section metadata
        4. Send to Groq LLM
        5. Return answer, sources, pages, sections, and retrieved_chunks
        """
        logger.info(f"RAG Engine query for User '{user_id}', Doc '{document_id}': {question}")

        # 1. Validate Document Access
        if not self.validate_document_access(user_id=user_id, document_id=document_id):
            logger.warning(f"Access denied or document '{document_id}' not found for user '{user_id}'.")
            return {
                "answer": NO_INFORMATION_FALLBACK_RESPONSE,
                "sources": [],
                "pages": [],
                "sections": [],
                "retrieved_chunks": [],
            }

        # 2. Convert Question to Embedding & Retrieve Top-K Chunks from ChromaDB
        retrieved_chunks = self.vector_service.search(
            query_text=question,
            user_id=user_id,
            document_id=document_id,
            top_k=top_k,
        )

        if not retrieved_chunks:
            logger.info(f"No relevant vector chunks found for doc '{document_id}'.")
            return {
                "answer": NO_INFORMATION_FALLBACK_RESPONSE,
                "sources": [],
                "pages": [],
                "sections": [],
                "retrieved_chunks": [],
            }

        # 3. Collect Metadata Lists (Page Numbers, Sections, Sources)
        page_set = set()
        section_set = set()
        sources_list = []

        for chunk in retrieved_chunks:
            page_no = chunk.get("page_number")
            if page_no is not None:
                try:
                    page_set.add(int(page_no))
                except (ValueError, TypeError):
                    pass

            sec = chunk.get("section")
            if sec:
                section_set.add(str(sec).strip())

            txt = chunk.get("text", "")
            snippet = txt[:250] + "..." if len(txt) > 250 else txt
            sources_list.append(f"Page {page_no or 1} ({sec or 'Section'}): {snippet}")

        sorted_pages = sorted(list(page_set))
        sorted_sections = sorted(list(section_set))

        # 4. Construct Prompt
        formatted_context = self._format_context(retrieved_chunks)
        formatted_history = self._format_history(conversation_history)

        prompt = STRICT_RAG_SYSTEM_PROMPT.format(
            context=formatted_context,
            history=formatted_history,
            question=question,
        )

        # 5. Send to Groq LLM Client
        raw_answer = self.llm_client.generate(
            prompt=prompt,
            temperature=0.1,
        )

        # 6. Fallback Check
        if (
            not raw_answer
            or "could not find sufficient information" in raw_answer.lower()
            or "insufficient information" in raw_answer.lower()
        ):
            return {
                "answer": NO_INFORMATION_FALLBACK_RESPONSE,
                "sources": [],
                "pages": [],
                "sections": [],
                "retrieved_chunks": retrieved_chunks,
            }

        return {
            "answer": raw_answer,
            "sources": sources_list,
            "pages": sorted_pages,
            "sections": sorted_sections,
            "retrieved_chunks": retrieved_chunks,
        }
