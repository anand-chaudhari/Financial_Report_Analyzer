import re
from typing import List, Dict, Any, Optional
from ..vectorstore.chroma_client import ChromaVectorService
from ..llm.llm_client import LLMService
from .prompts import FINANCIAL_RAG_SYSTEM_PROMPT
from ..schemas.chat_schema import Citation, ChatQueryResponse
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

FALLBACK_PHRASE = "does not contain sufficient information"


class RAGPipeline:
    """Orchestrates retrieval-augmented generation for financial Q&A."""

    def __init__(self):
        self.vector_service = ChromaVectorService()
        self.llm_service = LLMService()

    def _format_context(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Formats chunks into numbered context blocks with page tags."""
        context_blocks = []
        for chunk in retrieved_chunks:
            page_no = chunk.get("page_number", 1)
            text = chunk.get("text", "")
            context_blocks.append(f"--- [Page {page_no}] ---\n{text}")
        return "\n\n".join(context_blocks)

    def _extract_citations(
        self, answer_text: str, retrieved_chunks: List[Dict[str, Any]]
    ) -> List[Citation]:
        """Extracts [Page X] tags from LLM answer and maps them to snippets."""
        page_matches = set(re.findall(r"\[Page\s*(\d+)\]", answer_text, re.IGNORECASE))
        citations: List[Citation] = []

        for page_str in page_matches:
            try:
                page_num = int(page_str)
                # Find matching chunk
                matching_chunk = next(
                    (c for c in retrieved_chunks if c.get("page_number") == page_num),
                    None
                )
                snippet = (
                    matching_chunk["text"][:250] + "..."
                    if matching_chunk else f"Content referenced from Page {page_num}"
                )
                citations.append(
                    Citation(
                        page_number=page_num,
                        snippet=snippet,
                        chunk_id=matching_chunk.get("chunk_id") if matching_chunk else None,
                        similarity_score=matching_chunk.get("similarity_score") if matching_chunk else None
                    )
                )
            except Exception:
                continue

        # Sort citations by page number
        citations.sort(key=lambda c: c.page_number)
        return citations

    def answer_query(
        self,
        report_id: str,
        question: str,
        user_id: Optional[str] = None,
        top_k: int = 4
    ) -> ChatQueryResponse:
        """Executes full RAG pipeline: retrieve -> prompt -> generate -> verify citations."""
        logger.info(f"Executing RAG query for report '{report_id}': {question}")

        # 1. Retrieve chunks from ChromaDB
        chunks = self.vector_service.query_similar_chunks(
            query_text=question,
            report_id=report_id,
            user_id=user_id,
            top_k=top_k
        )

        if not chunks:
            return ChatQueryResponse(
                answer="No relevant content found in the uploaded report for this query.",
                citations=[],
                is_grounded=False,
                source_found=False
            )

        # 2. Build prompt
        formatted_context = self._format_context(chunks)
        prompt = FINANCIAL_RAG_SYSTEM_PROMPT.format(
            context=formatted_context,
            question=question
        )

        # 3. Generate response
        raw_answer = self.llm_service.generate(prompt)

        # 4. Check for hallucination / fallback
        if FALLBACK_PHRASE.lower() in raw_answer.lower():
            return ChatQueryResponse(
                answer=raw_answer,
                citations=[],
                is_grounded=True,
                source_found=False
            )

        # 5. Extract citations
        citations = self._extract_citations(raw_answer, chunks)

        return ChatQueryResponse(
            answer=raw_answer,
            citations=citations,
            is_grounded=True,
            source_found=True
        )
