from dataclasses import dataclass
from typing import List, Dict, Any, Optional
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

from .pdf_extractor import ExtractedPage
from .cleaner import TextCleaner
from .section_detector import SectionDetector
from ..config import get_settings


@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: str
    user_id: str
    file_name: str
    company_name: str
    financial_year: str
    page_number: int
    section: str
    text: str
    metadata: Dict[str, Any]


class DocumentChunker:
    """
    Splits cleaned text into overlapping semantic chunks with configurable size/overlap.
    Attaches complete metadata dictionary to every chunk.
    """

    def __init__(self, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None):
        settings = get_settings()
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", "; ", " ", ""],
            length_function=len,
        )

    def chunk_pages(
        self,
        pages: List[ExtractedPage],
        document_id: str,
        user_id: str,
        file_name: str = "document.pdf",
        company_name: str = "Unknown Company",
        financial_year: str = "FY2024",
    ) -> List[DocumentChunk]:
        """
        Processes ExtractedPage list page-by-page, detects sections statefully,
        cleans text, splits into chunks, and attaches exact required metadata.
        """
        chunks: List[DocumentChunk] = []
        section_detector = SectionDetector()

        for page in pages:
            raw_text = (page.raw_text or "").strip()
            if not raw_text:
                continue

            cleaned_text = TextCleaner.clean(raw_text)
            if not cleaned_text or len(cleaned_text.strip()) < 5:
                cleaned_text = raw_text

            if not cleaned_text:
                continue

            # Update section context
            current_section = section_detector.update_and_get_section(cleaned_text)

            split_blocks = self.text_splitter.split_text(cleaned_text)
            if not split_blocks and cleaned_text:
                split_blocks = [cleaned_text]

            for idx, text_block in enumerate(split_blocks):
                chunk_id = f"{document_id}_p{page.page_number}_c{idx}"

                metadata = {
                    "document_id": document_id,
                    "user_id": user_id,
                    "file_name": file_name,
                    "company_name": company_name,
                    "financial_year": financial_year,
                    "page_number": page.page_number,
                    "section": current_section,
                    "chunk_id": chunk_id,
                    "chunk_index": idx,
                    "char_length": len(text_block),
                    "has_tables": page.has_tables,
                }

                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        user_id=user_id,
                        file_name=file_name,
                        company_name=company_name,
                        financial_year=financial_year,
                        page_number=page.page_number,
                        section=current_section,
                        text=text_block,
                        metadata=metadata,
                    )
                )

        return chunks


def chunk_document_pages(
    pages: List[ExtractedPage],
    report_id: str,
    user_id: str,
    file_name: str = "report.pdf",
    company_name: str = "Unknown Company",
    financial_year: str = "FY2024",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[DocumentChunk]:
    """Convenience function wrapper for DocumentChunker."""
    chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return chunker.chunk_pages(
        pages=pages,
        document_id=report_id,
        user_id=user_id,
        file_name=file_name,
        company_name=company_name,
        financial_year=financial_year,
    )
