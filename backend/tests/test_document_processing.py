import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from app.document_processing import (
    DocumentProcessor,
    TextCleaner,
    SectionDetector,
    DocumentChunker,
    OCRExtensionHook,
    PDFExtractor,
    ExtractedPage,
)


def create_sample_pdf_bytes():
    """Generates an in-memory PDF byte stream for testing extraction and chunking."""
    doc = fitz.open()

    # Page 1: Normal text with SEC Item 1A heading & financial numbers
    page1 = doc.new_page()
    rect = fitz.Rect(50, 50, 550, 700)
    page1.insert_textbox(
        rect,
        "UNITED STATES SECURITIES AND EXCHANGE COMMISSION\n"
        "FORM 10-K\n\n"
        "ITEM 1A. RISK FACTORS\n\n"
        "The Company operates in a highly competitive market. "
        "Gross margin was 46.2% in FY2024 compared to 44.1% in FY2023. "
        "Total revenue reached $391,035 million."
    )

    # Page 2: Item 8 Financial Statements table text
    page2 = doc.new_page()
    page2.insert_textbox(
        rect,
        "ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA\n\n"
        "CONSOLIDATED BALANCE SHEETS\n"
        "Cash and cash equivalents: $29,944 million.\n"
        "Net income for period ended September 28, 2024: $93,736 million.\n"
        "Diluted earnings per share: $6.08."
    )

    # Page 3: Empty page (blank)
    page3 = doc.new_page()

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def sample_pdf_bytes():
    return create_sample_pdf_bytes()


def test_pdf_extraction(sample_pdf_bytes):
    """Test 1: PDF extraction page-by-page and 1-indexed page numbering."""
    extractor = PDFExtractor()
    pages = extractor.extract(sample_pdf_bytes)

    assert len(pages) == 3
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert pages[2].page_number == 3

    assert "ITEM 1A. RISK FACTORS" in pages[0].raw_text
    assert "$391,035" in pages[0].raw_text
    assert "CONSOLIDATED BALANCE SHEETS" in pages[1].raw_text


def test_empty_page_handling(sample_pdf_bytes):
    """Test 2: Empty / scanned page detection."""
    extractor = PDFExtractor()
    pages = extractor.extract(sample_pdf_bytes)

    # Page 3 is empty
    assert pages[2].is_empty is True
    assert pages[2].char_count == 0

    # Page 1 & 2 are non-empty
    assert pages[0].is_empty is False
    assert pages[1].is_empty is False


def test_text_cleaning():
    """Test 3: Text cleaning while preserving financial figures, percentages, dates, and headers."""
    dirty_text = (
        "  ITEM 7.  MANAGEMENT'S   DISCUSSION \x00\x07 AND ANALYSIS  \n\n\n\n"
        "Revenue was   $383,285 million  (or  €350,000M)  with   growth of  +12.9%  \n"
        "as of  September 28, 2024.   \xa0  Losses were  (1,234.50)  points.  "
    )

    cleaned = TextCleaner.clean(dirty_text)

    # Asserts that redundant spaces and control chars are normalized
    assert "\x00" not in cleaned
    assert "\xa0" not in cleaned

    # Asserts financial numbers, percentages, dates, and currencies are preserved
    assert "$383,285" in cleaned
    assert "€350,000M" in cleaned
    assert "+12.9%" in cleaned
    assert "September 28, 2024" in cleaned
    assert "(1,234.50)" in cleaned
    assert "ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS" in cleaned


def test_section_detection():
    """Test 4: Detection of financial report headings and sections."""
    detector = SectionDetector()

    sec1 = detector.update_and_get_section("This page covers ITEM 1A. RISK FACTORS in detail.")
    assert sec1 == "Item 1A. Risk Factors"

    sec2 = detector.update_and_get_section("Here are CONSOLIDATED BALANCE SHEETS for FY2024.")
    assert sec2 == "Consolidated Balance Sheets"

    sec3 = detector.update_and_get_section("ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA")
    assert sec3 == "Item 8. Financial Statements & Supplementary Data"


def test_chunk_generation_and_metadata(sample_pdf_bytes):
    """Test 5: Chunk generation, configurable chunk size/overlap, and exact metadata preservation."""
    processor = DocumentProcessor(chunk_size=300, chunk_overlap=50)

    doc_id = "doc_test_999"
    user_id = "user_test_456"
    file_name = "Apple_10K_FY24.pdf"
    company_name = "Apple Inc."
    financial_year = "FY2024"

    result = processor.process_pdf(
        pdf_source=sample_pdf_bytes,
        document_id=doc_id,
        user_id=user_id,
        file_name=file_name,
        company_name=company_name,
        financial_year=financial_year,
    )

    assert result.document_id == doc_id
    assert result.user_id == user_id
    assert result.total_pages == 3
    assert result.non_empty_pages == 2
    assert result.total_chunks > 0

    # Verify every chunk contains all 8 required metadata fields
    required_keys = {
        "document_id",
        "user_id",
        "file_name",
        "company_name",
        "financial_year",
        "page_number",
        "section",
        "chunk_id",
    }

    for chunk in result.chunks:
        assert isinstance(chunk.chunk_id, str)
        assert len(chunk.text) > 0
        assert required_keys.issubset(set(chunk.metadata.keys()))

        # Check values
        assert chunk.metadata["document_id"] == doc_id
        assert chunk.metadata["user_id"] == user_id
        assert chunk.metadata["file_name"] == file_name
        assert chunk.metadata["company_name"] == company_name
        assert chunk.metadata["financial_year"] == financial_year
        assert chunk.metadata["page_number"] in [1, 2]
        assert isinstance(chunk.metadata["section"], str)


def test_ocr_extension_hook():
    """Test 6: OCRExtensionHook inspection for scanned pages."""
    hook = OCRExtensionHook(min_char_threshold=40)

    is_empty, is_scanned = hook.inspect_page(raw_text="", image_count=0)
    assert is_empty is True
    assert is_scanned is False

    is_empty, is_scanned = hook.inspect_page(raw_text="Short", image_count=2)
    assert is_empty is False
    assert is_scanned is True


if __name__ == "__main__":
    print("Running test suite for PDF document processing pipeline...")
    pdf_bytes = create_sample_pdf_bytes()
    test_pdf_extraction(pdf_bytes)
    print("[PASS] Test 1 Passed: PDF Extraction")
    test_empty_page_handling(pdf_bytes)
    print("[PASS] Test 2 Passed: Empty Page Handling")
    test_text_cleaning()
    print("[PASS] Test 3 Passed: Text Cleaning")
    test_section_detection()
    print("[PASS] Test 4 Passed: Section Detection")
    test_chunk_generation_and_metadata(pdf_bytes)
    print("[PASS] Test 5 Passed: Chunk Generation & Metadata Preservation")
    test_ocr_extension_hook()
    print("[PASS] Test 6 Passed: OCR Extension Hook")
    print("\nALL 6 UNIT TESTS PASSED SUCCESSFULLY!")

