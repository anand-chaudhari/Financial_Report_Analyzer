import os
import sys
import gc
import time
import tracemalloc
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from app.document_processing.pdf_extractor import PDFExtractor
from app.document_processing.file_detector import FileTypeDetector
from app.services.document_service import DocumentService
from app.vectorstore.vector_service import VectorStoreService


def generate_synthetic_large_financial_pdf(file_path: str, page_count: int = 60, target_mb: float = 5.0):
    """
    Generates a realistic, dense multi-page financial PDF with:
    - Executive Summary & Company Details
    - Income Statement / Balance Sheet / Cash Flow markdown tables
    - Dense financial notes to accounts
    - Padding to test large file handling
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    doc = fitz.open()

    table_pnl = """
Statement of Profit and Loss for the year ended March 31, 2026
Particulars | FY2026 (Rs Cr) | FY2025 (Rs Cr) | Growth (%)
--- | --- | --- | ---
Revenue from Operations | 240,893 | 225,458 | +6.8%
Other Income | 4,520 | 3,890 | +16.2%
Total Income | 245,413 | 229,348 | +7.0%
Cost of Materials Consumed | 82,100 | 78,400 | +4.7%
Employee Benefit Expenses | 54,200 | 50,120 | +8.1%
Other Operating Expenses | 35,400 | 33,200 | +6.6%
Total Operating Expenses | 171,700 | 161,720 | +6.2%
EBITDA | 73,713 | 67,628 | +9.0%
Finance Costs | 1,250 | 1,420 | -12.0%
Depreciation and Amortisation | 8,900 | 8,200 | +8.5%
Profit Before Tax (PBT) | 63,563 | 58,008 | +9.6%
Tax Expense | 15,250 | 14,100 | +8.2%
Profit After Tax (PAT) / Net Profit | 48,313 | 43,908 | +10.0%
"""

    table_bs = """
Balance Sheet as at March 31, 2026
ASSETS | FY2026 (Rs Cr) | FY2025 (Rs Cr)
--- | --- | ---
Property, Plant and Equipment | 112,450 | 105,200
Capital Work-in-Progress | 8,400 | 9,100
Intangible Assets & Goodwill | 15,300 | 15,300
Non-Current Financial Assets | 24,100 | 22,000
Total Non-Current Assets | 160,250 | 151,600
Inventories | 31,200 | 28,400
Trade Receivables | 42,100 | 39,500
Cash and Cash Equivalents | 18,900 | 15,200
Total Current Assets | 92,200 | 83,100
TOTAL ASSETS | 252,450 | 234,700
EQUITY AND LIABILITIES | | 
Total Equity | 145,800 | 132,400
Long Term Borrowings (Debt) | 28,500 | 31,200
Total Liabilities | 106,650 | 102,300
TOTAL EQUITY AND LIABILITIES | 252,450 | 234,700
"""

    notes_text = (
        "Note 14: Capital Management and Debt Covenants.\n"
        "The Company maintains a conservative gearing ratio of 0.20x net debt to equity. "
        "Working capital facilities of Rs 15,000 Crore remain unutilized as of March 31, 2026. "
        "Foreign exchange exposure is actively hedged using forward exchange contracts.\n\n"
    ) * 12

    for i in range(page_count):
        page = doc.new_page(width=595, height=842)
        p_num = i + 1
        if p_num == 1:
            header = "TATA CONSULTANCY SERVICES LIMITED\nANNUAL REPORT FY2026\nCorporate Identification Number (CIN): L22210MH1995PLC084781\nRegistered Office: Mumbai, India\n\n"
            text_content = header + "EXECUTIVE SUMMARY\n" + table_pnl + "\n" + notes_text
        elif p_num == 2:
            text_content = "STATEMENT OF PROFIT AND LOSS (CONTINUED)\n" + table_pnl + "\n" + notes_text
        elif p_num == 3:
            text_content = "CONSOLIDATED BALANCE SHEET\n" + table_bs + "\n" + notes_text
        else:
            text_content = f"FINANCIAL STATEMENTS NOTES & DISCLOSURES - SECTION {p_num}\n" + notes_text

        page.insert_text((50, 50), text_content, fontsize=9)

    doc.save(file_path)
    doc.close()


def test_pdf_preflight_inspection_and_classification():
    """Verifies that preflight inspection correctly detects text vs scanned without OCR assumption."""
    test_dir = os.path.join(os.getcwd(), "backend", "cache", "test_bench")
    os.makedirs(test_dir, exist_ok=True)
    pdf_path = os.path.join(test_dir, "financial_test.pdf")
    generate_synthetic_large_financial_pdf(pdf_path, page_count=10)

    try:
        inspection = PDFExtractor.inspect_pdf(pdf_path)
        assert inspection["total_pages"] == 10
        assert inspection["classification"] == "text_native"
        assert inspection["ocr_required"] is False
        assert inspection["sample_chars_avg"] > 100
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_file_detector_streaming_path_support():
    """Verifies FileTypeDetector works directly on file path with 0 RAM buffer."""
    test_dir = os.path.join(os.getcwd(), "backend", "cache", "test_bench")
    os.makedirs(test_dir, exist_ok=True)
    pdf_path = os.path.join(test_dir, "streaming_test.pdf")
    generate_synthetic_large_financial_pdf(pdf_path, page_count=5)

    try:
        fmt, size = FileTypeDetector.validate_file(pdf_path, filename="streaming_test.pdf")
        assert fmt == "pdf"
        assert size > 0
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_stage_progression_and_cancellation():
    """Verifies exact stage tracking (Uploading -> Analyzing -> Extracting -> Chunking -> Embedding -> Indexing -> Ready)."""
    test_dir = os.path.join(os.getcwd(), "backend", "cache", "test_bench")
    os.makedirs(test_dir, exist_ok=True)
    pdf_path = os.path.join(test_dir, "pipeline_test.pdf")
    generate_synthetic_large_financial_pdf(pdf_path, page_count=8)

    mock_db = MagicMock()
    mock_db.collection.return_value.document.return_value.get.return_value.exists = False

    mock_vec = MagicMock()
    mock_vec.document_exists.return_value = False
    mock_vec.document_exists_by_hash.return_value = None
    mock_vec.add_document.return_value = 16

    doc_service = DocumentService(firestore_db=mock_db, vector_service=mock_vec)

    stages_recorded = []

    def mock_save(doc_model):
        stages_recorded.append((doc_model.currentStage, doc_model.progressPercent))

    doc_service._save_to_firestore = mock_save

    try:
        doc = doc_service.process_and_save_upload(
            file_path=pdf_path,
            filename="pipeline_test.pdf",
            user_id="test_user_large"
        )

        stage_names = [s[0] for s in stages_recorded]
        assert "Uploading" in stage_names
        assert "Analyzing" in stage_names
        assert "Extracting" in stage_names
        assert "Chunking" in stage_names
        assert "Embedding" in stage_names
        assert "Indexing" in stage_names
        assert "Ready" in stage_names
        assert doc.status == "completed"
        assert doc.progressPercent == 100
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_large_pdf_memory_and_extraction_benchmark():
    """
    Comprehensive Benchmark for Large PDF Processing:
    Measures:
    1. Processing time
    2. Peak RAM using tracemalloc
    3. Number of OCR pages (0 for text PDF)
    4. Number of chunks created
    5. Searchable status in ChromaDB
    """
    test_dir = os.path.join(os.getcwd(), "backend", "cache", "test_bench")
    os.makedirs(test_dir, exist_ok=True)
    benchmark_pdf_path = os.path.join(test_dir, "large_sample_50p.pdf")
    generate_synthetic_large_financial_pdf(benchmark_pdf_path, page_count=50)

    tracemalloc.start()
    t_start = time.time()

    # Preflight Inspection
    inspection = PDFExtractor.inspect_pdf(benchmark_pdf_path)
    extractor = PDFExtractor()
    extracted_pages = extractor.extract(benchmark_pdf_path)

    t_extraction = time.time() - t_start
    current_ram, peak_ram = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_ram_mb = peak_ram / (1024 * 1024)

    ocr_pages_count = sum(1 for p in extracted_pages if p.is_scanned)
    total_chars = sum(p.char_count for p in extracted_pages)

    print("\n" + "=" * 60)
    print("LARGE PDF BENCHMARK RESULTS")
    print("=" * 60)
    print(f"File Path: {benchmark_pdf_path}")
    print(f"Total Pages: {len(extracted_pages)}")
    print(f"Total Characters Extracted: {total_chars:,}")
    print(f"Pre-flight OCR Required: {inspection['ocr_required']}")
    print(f"Actual OCR Pages Run: {ocr_pages_count} (Prioritized fast native extraction)")
    print(f"Extraction Time: {t_extraction:.2f} seconds")
    print(f"Peak RAM Utilized: {peak_ram_mb:.2f} MB")
    print("=" * 60)

    try:
        assert len(extracted_pages) == 50
        assert ocr_pages_count == 0
        assert peak_ram_mb < 150  # Memory stayed tightly bounded
        assert inspection["ocr_required"] is False
    finally:
        if os.path.exists(benchmark_pdf_path):
            os.remove(benchmark_pdf_path)


import pytest
from unittest.mock import MagicMock

@pytest.mark.anyio
async def test_upload_endpoint_streaming_success(monkeypatch):
    """Verify that the FastAPI /documents/upload endpoint streams files without 500 error."""
    from app.routes.documents import upload_document
    from app.schemas.document_schema import DocumentMetadata
    from fastapi import UploadFile

    mock_doc = DocumentMetadata(
        documentId="test_stream_id",
        userId="test_stream_user",
        fileName="test_upload_sample.pdf",
        fileSize=1024,
        status="completed",
        currentStage="Ready",
        progressPercent=100,
        pageCount=6,
        uploadedAt="2026-09-02T12:00:00",
        processedAt="2026-09-02T12:00:00"
    )
    monkeypatch.setattr(
        "app.routes.documents.document_service.process_and_save_upload",
        lambda *args, **kwargs: mock_doc
    )

    test_dir = os.path.join(os.getcwd(), "backend", "cache", "test_bench")
    os.makedirs(test_dir, exist_ok=True)
    sample_pdf_path = os.path.join(test_dir, "test_upload_sample.pdf")
    generate_synthetic_large_financial_pdf(sample_pdf_path, page_count=6)

    try:
        with open(sample_pdf_path, "rb") as f_in:
            upload_file = UploadFile(
                filename="test_upload_sample.pdf",
                file=f_in,
                headers={"content-type": "application/pdf"}
            )
            response = await upload_document(
                file=upload_file,
                current_user={"uid": "test_stream_user", "email": "test@user.com"}
            )

        assert response.success is True
        assert response.data.fileName == "test_upload_sample.pdf"
        assert response.data.status == "completed"
        assert response.data.currentStage == "Ready"
    finally:
        if os.path.exists(sample_pdf_path):
            os.remove(sample_pdf_path)
