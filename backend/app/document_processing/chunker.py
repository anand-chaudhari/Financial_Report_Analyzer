from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union
from .models import (
    ExtractedDocument,
    DocumentSection,
    DocumentBlock,
    SourceLocation,
    ExtractedPage,
)
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


def _fast_split_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Ultra-fast high-performance sliding-window text chunker for financial text.
    Preserves paragraphs, tables, and sentence boundaries without slow recursion.
    """
    if not text:
        return []

    text_len = len(text)
    if text_len <= chunk_size:
        return [text]

    chunks = []
    # Split text primarily into paragraph blocks
    paragraphs = text.split("\n\n")
    current_chunk = []
    current_len = 0

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        p_len = len(p)

        # If a single paragraph/table is larger than chunk_size, split by lines
        if p_len > chunk_size:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_len = 0

            lines = p.split("\n")
            sub_chunk = []
            sub_len = 0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if sub_len + len(line) + 1 > chunk_size and sub_chunk:
                    chunks.append("\n".join(sub_chunk))
                    overlap_line = sub_chunk[-1] if len(sub_chunk[-1]) < chunk_overlap else ""
                    sub_chunk = [overlap_line, line] if overlap_line else [line]
                    sub_len = sum(len(x) + 1 for x in sub_chunk)
                else:
                    sub_chunk.append(line)
                    sub_len += len(line) + 1
            if sub_chunk:
                chunks.append("\n".join(sub_chunk))

        elif current_len + p_len + 2 <= chunk_size:
            current_chunk.append(p)
            current_len += p_len + 2
        else:
            chunks.append("\n\n".join(current_chunk))
            overlap_p = current_chunk[-1] if current_chunk and len(current_chunk[-1]) <= chunk_overlap else ""
            current_chunk = [overlap_p, p] if overlap_p else [p]
            current_len = sum(len(x) + 2 for x in current_chunk)

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks if chunks else [text]


class DocumentChunker:
    """
    High-performance multi-format financial chunker.
    Preserves table structure, heading hierarchy, sheet context, and source locations.
    """

    def __init__(self, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None):
        settings = get_settings()
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def chunk_document(
        self,
        doc: ExtractedDocument,
        user_id: str,
    ) -> List[DocumentChunk]:
        """
        Chunks a normalized ExtractedDocument into semantic vector chunks while preserving
        exact source locations (Sheet, Page, Section, Row Range) and financial table integrity.
        """
        chunks: List[DocumentChunk] = []
        chunk_idx = 0

        company = doc.company_name or "Financial Entity"
        fy = doc.financial_year or "FY2026"
        file_name = doc.file_name
        doc_id = doc.document_id

        for s_idx, section in enumerate(doc.sections, 1):
            sec_name = section.section_name or "General"
            sec_loc = section.source_location
            sec_citation = sec_loc.get_citation_label()

            # Group section blocks
            combined_blocks: List[str] = []
            block_locations: List[str] = []

            for b in section.blocks:
                b_content = (b.content or "").strip()
                if not b_content:
                    continue

                b_loc = b.source_location
                b_citation = b_loc.get_citation_label() if b_loc else sec_citation

                # Clean text block if plain text
                if b.block_type == "text":
                    b_clean = TextCleaner.clean(b_content)
                    if b_clean and len(b_clean) >= 5:
                        b_content = b_clean

                # Check if block is a structured markdown table
                if b.block_type == "table":
                    # Tables get dedicated or prioritized chunking to avoid cutting rows
                    table_chunks = _fast_split_text(b_content, chunk_size=self.chunk_size * 2, chunk_overlap=self.chunk_overlap)
                    for t_chunk in table_chunks:
                        chunk_idx += 1
                        c_id = f"{doc_id}_s{s_idx}_c{chunk_idx}"
                        
                        pg_no = b_loc.page_number if (b_loc and b_loc.page_number) else (sec_loc.page_number if sec_loc else 1)
                        
                        meta = {
                            "document_id": doc_id,
                            "report_id": doc_id,
                            "user_id": user_id,
                            "file_name": file_name,
                            "file_type": doc.file_type,
                            "company_name": company,
                            "financial_year": fy,
                            "page_number": pg_no,
                            "sheet_name": b_loc.sheet_name if b_loc else "",
                            "row_range": b_loc.row_range if b_loc else "",
                            "section": sec_name,
                            "source_location": b_citation,
                            "chunk_id": c_id,
                            "chunk_index": chunk_idx,
                            "char_length": len(t_chunk),
                            "is_table": True,
                            "currency": doc.currency or "",
                            "units": doc.units or "",
                        }

                        chunks.append(DocumentChunk(
                            chunk_id=c_id,
                            document_id=doc_id,
                            user_id=user_id,
                            file_name=file_name,
                            company_name=company,
                            financial_year=fy,
                            page_number=pg_no,
                            section=sec_name,
                            text=t_chunk,
                            metadata=meta,
                        ))
                else:
                    combined_blocks.append(b_content)
                    block_locations.append(b_citation)

            # Process non-table text blocks in this section
            if combined_blocks:
                sec_text = "\n\n".join(combined_blocks)
                split_chunks = _fast_split_text(sec_text, chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
                for t_text in split_chunks:
                    chunk_idx += 1
                    c_id = f"{doc_id}_s{s_idx}_c{chunk_idx}"
                    pg_no = sec_loc.page_number if (sec_loc and sec_loc.page_number) else 1
                    
                    meta = {
                        "document_id": doc_id,
                        "report_id": doc_id,
                        "user_id": user_id,
                        "file_name": file_name,
                        "file_type": doc.file_type,
                        "company_name": company,
                        "financial_year": fy,
                        "page_number": pg_no,
                        "sheet_name": sec_loc.sheet_name if sec_loc else "",
                        "row_range": sec_loc.row_range if sec_loc else "",
                        "section": sec_name,
                        "source_location": sec_citation,
                        "chunk_id": c_id,
                        "chunk_index": chunk_idx,
                        "char_length": len(t_text),
                        "is_table": False,
                        "currency": doc.currency or "",
                        "units": doc.units or "",
                    }

                    chunks.append(DocumentChunk(
                        chunk_id=c_id,
                        document_id=doc_id,
                        user_id=user_id,
                        file_name=file_name,
                        company_name=company,
                        financial_year=fy,
                        page_number=pg_no,
                        section=sec_name,
                        text=t_text,
                        metadata=meta,
                    ))

        return chunks

    def chunk_pages(
        self,
        pages: List[ExtractedPage],
        document_id: str,
        user_id: str,
        file_name: str = "document.pdf",
        company_name: str = "Unknown Company",
        financial_year: str = "FY2024",
    ) -> List[DocumentChunk]:
        """Backward-compatible chunking method for raw ExtractedPage lists."""
        chunks: List[DocumentChunk] = []
        section_detector = SectionDetector()

        for page in pages:
            raw_text = (page.raw_text if hasattr(page, 'raw_text') else page.text or "").strip()
            if not raw_text:
                continue

            cleaned_text = TextCleaner.clean(raw_text)
            if not cleaned_text or len(cleaned_text.strip()) < 5:
                cleaned_text = raw_text

            if not cleaned_text:
                continue

            current_section = section_detector.update_and_get_section(cleaned_text)

            split_blocks = _fast_split_text(
                cleaned_text,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            if not split_blocks:
                split_blocks = [cleaned_text]

            for idx, text_block in enumerate(split_blocks):
                chunk_id = f"{document_id}_p{page.page_number}_c{idx}"
                loc_str = f"Page {page.page_number}"

                metadata = {
                    "document_id": document_id,
                    "report_id": document_id,
                    "user_id": user_id,
                    "file_name": file_name,
                    "file_type": "pdf",
                    "company_name": company_name,
                    "financial_year": financial_year,
                    "page_number": page.page_number,
                    "section": current_section,
                    "source_location": loc_str,
                    "chunk_id": chunk_id,
                    "chunk_index": idx,
                    "char_length": len(text_block),
                    "has_tables": getattr(page, 'has_tables', bool(getattr(page, 'tables', False))),
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
