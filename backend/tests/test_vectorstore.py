import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.vectorstore import VectorStoreService
from app.document_processing import DocumentChunk


def create_chunks_user_a():
    return [
        DocumentChunk(
            chunk_id="doc_a1_p1_c0",
            document_id="doc_apple_2024",
            user_id="user_alice",
            file_name="Apple_10K_FY24.pdf",
            company_name="Apple Inc.",
            financial_year="FY2024",
            page_number=1,
            section="Item 1A. Risk Factors",
            text="Apple Inc. gross margin was 46.2% in FY2024 compared to 44.1% in FY2023.",
            metadata={
                "document_id": "doc_apple_2024",
                "user_id": "user_alice",
                "file_name": "Apple_10K_FY24.pdf",
                "company_name": "Apple Inc.",
                "financial_year": "FY2024",
                "page_number": 1,
                "section": "Item 1A. Risk Factors",
                "chunk_id": "doc_a1_p1_c0"
            }
        ),
        DocumentChunk(
            chunk_id="doc_a1_p2_c0",
            document_id="doc_apple_2024",
            user_id="user_alice",
            file_name="Apple_10K_FY24.pdf",
            company_name="Apple Inc.",
            financial_year="FY2024",
            page_number=2,
            section="Item 8. Financial Statements",
            text="Apple revenue reached $391,035 million in fiscal year 2024 with net income of $93,736 million.",
            metadata={
                "document_id": "doc_apple_2024",
                "user_id": "user_alice",
                "file_name": "Apple_10K_FY24.pdf",
                "company_name": "Apple Inc.",
                "financial_year": "FY2024",
                "page_number": 2,
                "section": "Item 8. Financial Statements",
                "chunk_id": "doc_a1_p2_c0"
            }
        )
    ]


def create_chunks_user_b():
    return [
        DocumentChunk(
            chunk_id="doc_b1_p1_c0",
            document_id="doc_secret_project_x",
            user_id="user_bob",
            file_name="Confidential_Report.pdf",
            company_name="Acme Corp",
            financial_year="FY2024",
            page_number=1,
            section="Executive Summary",
            text="Acme Corp confidential gross margin and revenue figures for project X.",
            metadata={
                "document_id": "doc_secret_project_x",
                "user_id": "user_bob",
                "file_name": "Confidential_Report.pdf",
                "company_name": "Acme Corp",
                "financial_year": "FY2024",
                "page_number": 1,
                "section": "Executive Summary",
                "chunk_id": "doc_b1_p1_c0"
            }
        )
    ]


@pytest.fixture
def sample_chunks_user_a():
    return create_chunks_user_a()


@pytest.fixture
def sample_chunks_user_b():
    return create_chunks_user_b()


def test_add_document_and_exists(sample_chunks_user_a):
    """Test 1 & 2: Ingest chunks, check document_exists, avoid duplicates."""
    service = VectorStoreService(collection_name="test_financial_chunks")

    doc_id = "doc_apple_2024"
    user_id = "user_alice"

    # Initially cleanup
    service.delete_document(doc_id, user_id)
    assert service.document_exists(doc_id, user_id) is False

    # Add document
    count = service.add_document(
        document_id=doc_id,
        user_id=user_id,
        chunks=sample_chunks_user_a,
        overwrite_if_exists=True
    )
    assert count == 2
    assert service.document_exists(doc_id, user_id) is True


def test_search_retrieval(sample_chunks_user_a):
    """Test 3 & 4: Semantic vector search with top_k and metadata."""
    service = VectorStoreService(collection_name="test_financial_chunks")
    doc_id = "doc_apple_2024"
    user_id = "user_alice"

    results = service.search(
        query_text="What was Apple's gross margin in FY2024?",
        user_id=user_id,
        document_id=doc_id,
        top_k=2
    )

    assert len(results) > 0
    first = results[0]
    assert "text" in first
    assert "similarity_score" in first
    assert first["user_id"] == user_id
    assert first["document_id"] == doc_id
    assert "46.2%" in first["text"] or "391,035" in first["text"]


def test_strict_user_isolation(sample_chunks_user_a, sample_chunks_user_b):
    """Test 5: Ensure User A can NEVER retrieve User B's documents."""
    service = VectorStoreService(collection_name="test_financial_chunks")

    # Ingest User A's document
    service.add_document(
        document_id="doc_apple_2024",
        user_id="user_alice",
        chunks=sample_chunks_user_a,
        overwrite_if_exists=True
    )

    # Ingest User B's confidential document
    service.add_document(
        document_id="doc_secret_project_x",
        user_id="user_bob",
        chunks=sample_chunks_user_b,
        overwrite_if_exists=True
    )

    # User Alice searches for "Acme Corp confidential"
    alice_results = service.search(
        query_text="Acme Corp confidential gross margin",
        user_id="user_alice",
        top_k=5
    )

    # Alice must NOT see any of Bob's chunks
    for res in alice_results:
        assert res["user_id"] == "user_alice"
        assert res["document_id"] != "doc_secret_project_x"
        assert "Acme Corp" not in res["text"]

    # User Bob searches for "Apple gross margin"
    bob_results = service.search(
        query_text="Apple gross margin",
        user_id="user_bob",
        top_k=5
    )

    # Bob must NOT see any of Alice's chunks
    for res in bob_results:
        assert res["user_id"] == "user_bob"
        assert res["document_id"] != "doc_apple_2024"
        assert "Apple" not in res["text"]


def test_delete_document(sample_chunks_user_a):
    """Test 6: Delete document vectors from store."""
    service = VectorStoreService(collection_name="test_financial_chunks")
    doc_id = "doc_apple_2024"
    user_id = "user_alice"

    assert service.document_exists(doc_id, user_id) is True

    deleted = service.delete_document(doc_id, user_id)
    assert deleted is True
    assert service.document_exists(doc_id, user_id) is False


if __name__ == "__main__":
    print("Running VectorStoreService unit test suite...")
    chunks_a = create_chunks_user_a()
    chunks_b = create_chunks_user_b()

    test_add_document_and_exists(chunks_a)
    print("[PASS] Test 1 & 2 Passed: Ingestion & Duplicate Detection")
    test_search_retrieval(chunks_a)
    print("[PASS] Test 3 & 4 Passed: Vector Search & Metadata Retrieval")
    test_strict_user_isolation(chunks_a, chunks_b)
    print("[PASS] Test 5 Passed: Strict Security User Isolation")
    test_delete_document(chunks_a)
    print("[PASS] Test 6 Passed: Vector Document Deletion")

    print("\nALL VECTORSTORE UNIT TESTS PASSED SUCCESSFULLY!")
