import json
import re
import hashlib
from typing import Optional, Callable, List, Dict, Any, Union
from .base_extractor import BaseDocumentExtractor
from ..models import (
    ExtractedDocument,
    DocumentSection,
    DocumentBlock,
    ExtractedTable,
    SourceLocation,
)
from ...utils.logger import setup_logger

logger = setup_logger(__name__)


class JSONExtractor(BaseDocumentExtractor):
    """
    Extracts structured JSON financial documents, converting nested objects and arrays
    into clearly organized sections, key-value summaries, and Markdown tables.
    """

    def extract(
        self,
        file_bytes: bytes,
        document_id: str,
        filename: str,
        user_id: Optional[str] = None,
        company_name: Optional[str] = None,
        financial_year: Optional[str] = None,
        on_progress: Optional[Callable[[str, int, str], None]] = None,
    ) -> ExtractedDocument:
        doc_hash = hashlib.sha256(file_bytes).hexdigest()

        if on_progress:
            on_progress("Parsing JSON", 25, f"Parsing structured JSON financial tree from {filename}")

        try:
            raw_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raw_text = file_bytes.decode("latin-1", errors="ignore")

        try:
            data = json.loads(raw_text)
        except Exception as e:
            raise ValueError(f"Invalid JSON syntax in '{filename}': {str(e)}")

        sections_map: Dict[str, List[DocumentBlock]] = {}
        sections_tables: Dict[str, List[ExtractedTable]] = {}

        detected_company = company_name
        detected_year = financial_year
        detected_currency = None
        detected_units = None

        # Recursively process JSON nodes
        self._process_json_node(
            node=data,
            path="",
            sections_map=sections_map,
            sections_tables=sections_tables,
        )

        # Detect metadata from top-level keys
        if isinstance(data, dict):
            for k, v in data.items():
                k_low = str(k).lower()
                if not detected_company and any(ck in k_low for ck in ("company", "entity", "issuer", "corporation")) and isinstance(v, str):
                    detected_company = v
                if not detected_year and any(yk in k_low for yk in ("year", "financial_year", "fiscal_year", "period")) and isinstance(v, (str, int)):
                    detected_year = str(v)
                if not detected_currency and "currency" in k_low and isinstance(v, str):
                    detected_currency = v
                if not detected_units and "unit" in k_low and isinstance(v, str):
                    detected_units = v

        if not sections_map:
            # Flat JSON representation
            loc = SourceLocation(format_type="json", node_path="root", human_label='JSON "root"')
            flat_text = json.dumps(data, indent=2)
            sections_map["General Financial Data"] = [
                DocumentBlock(block_type="text", content=flat_text, source_location=loc, section="General Financial Data")
            ]
            sections_tables["General Financial Data"] = []

        doc_sections: List[DocumentSection] = []
        for sec_name, blks in sections_map.items():
            loc = SourceLocation(
                format_type="json",
                node_path=sec_name,
                human_label=f'JSON "{sec_name}"'
            )
            raw_sec_text = "\n\n".join([b.content for b in blks])
            doc_sections.append(DocumentSection(
                section_name=sec_name,
                source_location=loc,
                blocks=blks,
                raw_text=raw_sec_text,
                tables=sections_tables.get(sec_name, []),
                metadata={"blocks_count": len(blks)}
            ))

        return ExtractedDocument(
            document_id=document_id,
            file_name=filename,
            file_type="json",
            file_size=len(file_bytes),
            doc_hash=doc_hash,
            company_name=detected_company,
            financial_year=detected_year,
            currency=detected_currency,
            units=detected_units,
            sections=doc_sections,
            pages_or_sheets_count=len(doc_sections),
            metadata={"sections_count": len(doc_sections)}
        )

    def _process_json_node(
        self,
        node: Any,
        path: str,
        sections_map: Dict[str, List[DocumentBlock]],
        sections_tables: Dict[str, List[ExtractedTable]],
    ):
        current_section = path if path else "Financial Summary"

        if isinstance(node, dict):
            # Check if this dict has sub-objects or is a key-value metrics sheet
            kv_pairs = []
            nested_items = []

            for k, v in node.items():
                sub_path = f"{path}.{k}" if path else str(k)
                if isinstance(v, (dict, list)):
                    nested_items.append((k, v, sub_path))
                else:
                    kv_pairs.append((str(k), str(v)))

            if kv_pairs:
                if current_section not in sections_map:
                    sections_map[current_section] = []
                    sections_tables[current_section] = []

                loc = SourceLocation(format_type="json", node_path=current_section, human_label=f'JSON "{current_section}"')

                # Format key-values as a clean two-column markdown table
                headers = ["Metric / Field", "Value"]
                rows = [[k, v] for k, v in kv_pairs]
                ext_table = ExtractedTable(
                    table_id=f"tbl_json_{current_section.replace('.', '_')}",
                    headers=headers,
                    rows=rows,
                    title=current_section,
                    source_location=loc,
                    table_type="key_value"
                )
                tbl_md = ext_table.to_markdown()
                sections_tables[current_section].append(ext_table)
                sections_map[current_section].append(DocumentBlock(
                    block_type="table",
                    content=tbl_md,
                    table=ext_table,
                    source_location=loc,
                    section=current_section
                ))

            for k, v, sub_path in nested_items:
                self._process_json_node(v, sub_path, sections_map, sections_tables)

        elif isinstance(node, list):
            if not node:
                return

            # Check if list of dicts (tabular dataset)
            if all(isinstance(item, dict) for item in node):
                if current_section not in sections_map:
                    sections_map[current_section] = []
                    sections_tables[current_section] = []

                loc = SourceLocation(format_type="json", node_path=current_section, human_label=f'JSON "{current_section}"')

                # Extract unified headers
                all_keys = []
                for item in node:
                    for k in item.keys():
                        if k not in all_keys:
                            all_keys.append(str(k))

                rows = []
                for item in node:
                    row = [str(item.get(k, "")) for k in all_keys]
                    rows.append(row)

                ext_table = ExtractedTable(
                    table_id=f"tbl_json_arr_{current_section.replace('.', '_')}",
                    headers=all_keys,
                    rows=rows,
                    title=current_section,
                    source_location=loc,
                    table_type="financial_dataset"
                )
                tbl_md = ext_table.to_markdown()
                sections_tables[current_section].append(ext_table)
                sections_map[current_section].append(DocumentBlock(
                    block_type="table",
                    content=tbl_md,
                    table=ext_table,
                    source_location=loc,
                    section=current_section
                ))
            else:
                # List of primitives
                if current_section not in sections_map:
                    sections_map[current_section] = []
                    sections_tables[current_section] = []

                loc = SourceLocation(format_type="json", node_path=current_section, human_label=f'JSON "{current_section}"')
                list_text = "\n".join([f"- {str(item)}" for item in node])
                sections_map[current_section].append(DocumentBlock(
                    block_type="text",
                    content=list_text,
                    source_location=loc,
                    section=current_section
                ))
