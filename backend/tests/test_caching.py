import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.cache_service import AICacheService, get_ai_cache_service
from app.services.document_service import DocumentService
from app.services.summary_service import SummaryService
from app.services.financial_service import FinancialService
from app.services.comparison_service import ComparisonService


@pytest.fixture
def cache_service():
    return get_ai_cache_service()


def test_deterministic_cache_key_generation(cache_service):
    """Test deterministic composite cache key creation."""
    key1 = cache_service.build_cache_key("fin_overview", user_id="user_123", document_id="doc_abc")
    key2 = cache_service.build_cache_key("fin_overview", user_id="user_123", document_id="doc_abc")
    assert key1 == key2

    key_params1 = cache_service.build_cache_key("comparison", user_id="user_123", document_id="doc_a", document_b_id="doc_b", extra_params={"v": "2"})
    key_params2 = cache_service.build_cache_key("comparison", user_id="user_123", document_id="doc_a", document_b_id="doc_b", extra_params={"v": "2"})
    assert key_params1 == key_params2

    # Different params produce different keys
    key_params3 = cache_service.build_cache_key("comparison", user_id="user_123", document_id="doc_a", document_b_id="doc_b", extra_params={"v": "3"})
    assert key_params1 != key_params3


def test_cache_hit_and_miss_lifecycle(cache_service):
    """Test full cache lifecycle: MISS -> SAVE -> HIT -> REFRESH -> INVALIDATE."""
    test_key = "test_section_user1_doc999"
    
    # 1. Clean initial state
    cache_service.invalidate_document_cache("doc999")
    assert cache_service.get_cached_result(test_key) is None

    # 2. Save result
    sample_data = {"company": "Test Corp", "revenue": 1000, "status": "verified"}
    cache_service.save_result(test_key, "test_section", "user1", ["doc999"], sample_data)

    # 3. Retrieve result (CACHE HIT)
    cached_data = cache_service.get_cached_result(test_key)
    assert cached_data is not None
    assert cached_data["revenue"] == 1000

    # 4. Force refresh bypasses cache
    refreshed = cache_service.get_cached_result(test_key, force_refresh=True)
    assert refreshed is None

    # 5. Invalidate document cache
    cache_service.invalidate_document_cache("doc999")
    assert cache_service.get_cached_result(test_key) is None


def test_financial_overview_caching():
    """Verify that FinancialOverview caches output and avoids repeated LLM calls."""
    cache = get_ai_cache_service()
    doc_id = "doc_cache_test_overview"
    user_id = "user_cache_test"

    cache.invalidate_document_cache(doc_id)

    fin_service = FinancialService()
    
    # Mock LLM client so we can verify exact invocation count
    mock_llm = MagicMock()
    mock_llm.generate.return_value = json.dumps({
        "company_name": "Cached Financials Inc",
        "currency": "USD",
        "revenue": {"name": "Revenue", "fy2025_value": "1000", "fy2026_value": "1200", "growth": "+20%", "is_available": True},
        "net_profit": {"name": "Net Profit", "fy2025_value": "200", "fy2026_value": "250", "growth": "+25%", "is_available": True},
        "executive_overview": "Strong financial growth."
    })
    fin_service.llm_client = mock_llm

    # Mock vector service search
    fin_service.vector_service.search = MagicMock(return_value=[
        {"text": "Revenue reached $1200M in FY2026 compared to $1000M in FY2025.", "page_number": 1, "section": "Statement"}
    ])

    # Call 1: Should call LLM and store in cache
    res1 = fin_service.get_financial_overview(doc_id, user_id, force_refresh=False)
    assert res1.company_name == "Cached Financials Inc"
    assert mock_llm.generate.call_count == 1

    # Call 2 (Page reload / Tab switch): Should retrieve from cache directly WITHOUT calling LLM
    res2 = fin_service.get_financial_overview(doc_id, user_id, force_refresh=False)
    assert res2.company_name == "Cached Financials Inc"
    assert mock_llm.generate.call_count == 1  # Call count MUST remain 1!

    # Call 3 (User clicks explicit Refresh): Should regenerate and call LLM
    res3 = fin_service.get_financial_overview(doc_id, user_id, force_refresh=True)
    assert res3.company_name == "Cached Financials Inc"
    assert mock_llm.generate.call_count == 2  # Call count incremented to 2

    # Cleanup
    cache.invalidate_document_cache(doc_id)


def test_document_summary_caching():
    """Verify that SummaryService caches 11-section summary and avoids repeated LLM calls."""
    cache = get_ai_cache_service()
    doc_id = "doc_cache_test_summary"
    user_id = "user_cache_test"

    cache.invalidate_document_cache(doc_id)

    summary_service = SummaryService()
    
    # Mock LLM client
    mock_llm = MagicMock()
    mock_llm.generate.return_value = json.dumps({
        "executive_summary": "Executive summary content from filing.",
        "key_highlights": [{"title": "Growth", "description": "15% increase", "page_number": 1}],
        "revenue_analysis": {"title": "Revenue", "content": "1500M revenue", "page_number": 1},
        "profitability_analysis": {"title": "Profit", "content": "300M profit", "page_number": 1},
    })
    summary_service.llm_client = mock_llm

    # Mock document retrieval
    mock_doc = MagicMock()
    mock_doc.companyName = "Summary Corp"
    mock_doc.financialYear = "FY2026"
    mock_doc.fileName = "report.pdf"
    summary_service.document_service.get_document = MagicMock(return_value=mock_doc)

    mock_vector = MagicMock()
    mock_vector.document_exists.return_value = True
    mock_vector.search.return_value = [
        {"text": "Revenue grew by 15% to $1500M.", "page_number": 1, "section": "Financials"}
    ]
    mock_vector.collection.get.return_value = {
        "documents": [["Revenue grew by 15% to $1500M."]],
        "metadatas": [[{"page_number": 1, "section": "Financials"}]]
    }
    summary_service.vector_service = mock_vector

    with patch("app.services.summary_service.ensure_document_indexed"):
        with patch.object(summary_service, "_find_pdf_path", return_value=None):
            # Call 1: Generates and caches
            res1 = summary_service.generate_document_summary(doc_id, user_id, force_refresh=False)
            assert res1["executive_summary"]["text"] == "Executive summary content from filing."
            assert mock_llm.generate.call_count == 1

            # Call 2 (Page reload): Returns cached summary without calling LLM
            res2 = summary_service.generate_document_summary(doc_id, user_id, force_refresh=False)
            assert res2["executive_summary"]["text"] == "Executive summary content from filing."
            assert mock_llm.generate.call_count == 1  # Unchanged!

    # Cleanup
    cache.invalidate_document_cache(doc_id)
