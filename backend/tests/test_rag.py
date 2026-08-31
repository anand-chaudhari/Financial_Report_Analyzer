import pytest
from unittest.mock import MagicMock
from app.rag.rag_service import RAGService
from app.rag.prompts import NO_INFORMATION_FALLBACK_RESPONSE
from app.vectorstore.vector_service import VectorStoreService
from app.llm.llm_client import GroqLLMClient


def test_validate_document_access():
    mock_vector_service = MagicMock(spec=VectorStoreService)
    mock_vector_service.document_exists.side_effect = lambda document_id, user_id: (document_id == "doc_valid" and user_id == "user_alice")

    mock_llm_client = MagicMock(spec=GroqLLMClient)
    mock_doc_service = MagicMock()
    mock_doc_service.ensure_document_indexed.return_value = False
    rag_service = RAGService(vector_service=mock_vector_service, llm_client=mock_llm_client, document_service=mock_doc_service)

    assert rag_service.validate_document_access(user_id="user_alice", document_id="doc_valid") is True
    assert rag_service.validate_document_access(user_id="user_alice", document_id="doc_invalid") is False
    assert rag_service.validate_document_access(user_id="user_bob", document_id="doc_valid") is False
    print("[PASS] Test 1: Document Ownership Access Validation Passed.")


def test_rag_query_success():
    mock_vector_service = MagicMock(spec=VectorStoreService)
    mock_vector_service.document_exists.return_value = True
    mock_vector_service.search.return_value = [
        {
            "chunk_id": "c1",
            "text": "Total revenue for fiscal year 2024 reached $391.0 billion.",
            "page_number": 4,
            "section": "Item 7. MD&A",
            "similarity_score": 0.95,
        },
        {
            "chunk_id": "c2",
            "text": "Operating income was $123.2 billion with a 31.5% operating margin.",
            "page_number": 8,
            "section": "Item 8. Financial Statements",
            "similarity_score": 0.88,
        },
    ]

    mock_llm_client = MagicMock(spec=GroqLLMClient)
    mock_llm_client.generate.return_value = (
        "Total revenue for FY2024 was $391.0 billion [Page 4]. "
        "Operating income reached $123.2 billion [Page 8]."
    )

    rag_service = RAGService(vector_service=mock_vector_service, llm_client=mock_llm_client)
    res = rag_service.answer_question(
        user_id="user_alice",
        document_id="doc_valid",
        question="What was the FY2024 revenue?",
    )

    assert res["answer"] == (
        "Total revenue for FY2024 was $391.0 billion [Page 4]. "
        "Operating income reached $123.2 billion [Page 8]."
    )
    assert res["pages"] == [4, 8]
    assert res["sections"] == ["Item 7. MD&A", "Item 8. Financial Statements"]
    assert len(res["sources"]) == 2
    assert len(res["retrieved_chunks"]) == 2
    print("[PASS] Test 2: RAG Query Execution & Metadata Output Passed.")


def test_rag_query_no_information_fallback():
    mock_vector_service = MagicMock(spec=VectorStoreService)
    mock_vector_service.document_exists.return_value = True
    mock_vector_service.search.return_value = [
        {
            "chunk_id": "c1",
            "text": "The company operates in North America and Europe.",
            "page_number": 2,
            "section": "Overview",
            "similarity_score": 0.30,
        }
    ]

    mock_llm_client = MagicMock(spec=GroqLLMClient)
    mock_llm_client.generate.return_value = NO_INFORMATION_FALLBACK_RESPONSE

    rag_service = RAGService(vector_service=mock_vector_service, llm_client=mock_llm_client)
    res = rag_service.answer_question(
        user_id="user_alice",
        document_id="doc_valid",
        question="What is the CEO's personal home address?",
    )

    assert res["answer"] == NO_INFORMATION_FALLBACK_RESPONSE
    assert res["sources"] == []
    assert res["pages"] == []
    assert res["sections"] == []
    print("[PASS] Test 3: Grounded Fallback Response Passed.")


if __name__ == "__main__":
    test_validate_document_access()
    test_rag_query_success()
    test_rag_query_no_information_fallback()
    print("\nALL RAG ENGINE UNIT TESTS PASSED SUCCESSFULLY!")
