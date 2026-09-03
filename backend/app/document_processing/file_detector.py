import os
import io
import re
from typing import Tuple, Optional, Union


class UnsupportedFileFormatException(Exception):
    """Raised when an uploaded file is not in a supported financial document format or is corrupted."""
    pass


SUPPORTED_FORMATS = {
    "pdf": {
        "extensions": [".pdf"],
        "mimes": ["application/pdf"],
        "description": "Portable Document Format (PDF)",
        "max_size_bytes": 250 * 1024 * 1024,  # 250 MB
    },
    "xlsx": {
        "extensions": [".xlsx", ".xlsm", ".xltx", ".xltm"],
        "mimes": [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel.sheet.macroenabled.12",
        ],
        "description": "Microsoft Excel OpenXML Spreadsheet (XLSX)",
        "max_size_bytes": 100 * 1024 * 1024,  # 100 MB
    },
    "xls": {
        "extensions": [".xls"],
        "mimes": ["application/vnd.ms-excel"],
        "description": "Microsoft Excel Binary Spreadsheet (XLS)",
        "max_size_bytes": 100 * 1024 * 1024,  # 100 MB
    },
    "csv": {
        "extensions": [".csv", ".tsv"],
        "mimes": ["text/csv", "text/tab-separated-values", "text/plain"],
        "description": "Comma/Tab-Separated Values (CSV/TSV)",
        "max_size_bytes": 100 * 1024 * 1024,  # 100 MB
    },
    "docx": {
        "extensions": [".docx", ".docm", ".dotx"],
        "mimes": [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-word.document.macroenabled.12",
        ],
        "description": "Microsoft Word Document (DOCX)",
        "max_size_bytes": 150 * 1024 * 1024,  # 150 MB
    },
    "txt": {
        "extensions": [".txt", ".text", ".log"],
        "mimes": ["text/plain"],
        "description": "Plain Text Document (TXT)",
        "max_size_bytes": 50 * 1024 * 1024,   # 50 MB
    },
    "md": {
        "extensions": [".md", ".markdown"],
        "mimes": ["text/markdown", "text/plain", "text/x-markdown"],
        "description": "Markdown Document (MD)",
        "max_size_bytes": 50 * 1024 * 1024,   # 50 MB
    },
    "json": {
        "extensions": [".json"],
        "mimes": ["application/json", "text/json", "text/plain"],
        "description": "Structured JSON Document (JSON)",
        "max_size_bytes": 50 * 1024 * 1024,   # 50 MB
    },
}


class FileTypeDetector:
    """
    Detects and validates document file types using dual-layer inspection:
    1. Magic binary signatures & content patterns
    2. File extensions and MIME types
    """

    @staticmethod
    def detect_format(file_bytes_or_path: Union[bytes, str], filename: str, mime_type: Optional[str] = None) -> str:
        """
        Determines the normalized format key ('pdf', 'xlsx', 'xls', 'csv', 'docx', 'txt', 'md', 'json').
        Accepts either bytes or file path for streaming zero-memory overhead.
        """
        if isinstance(file_bytes_or_path, str):
            if not os.path.exists(file_bytes_or_path) or os.path.getsize(file_bytes_or_path) == 0:
                raise UnsupportedFileFormatException(f"File '{filename}' is empty (0 bytes) or does not exist.")
            with open(file_bytes_or_path, "rb") as f:
                header_bytes = f.read(8192)
        else:
            if not file_bytes_or_path:
                raise UnsupportedFileFormatException(f"The uploaded file '{filename}' is empty (0 bytes).")
            header_bytes = file_bytes_or_path[:8192]

        filename_clean = filename.strip()
        ext = os.path.splitext(filename_clean)[1].lower()

        # 1. Magic byte signatures
        header_16 = header_bytes[:16]

        # PDF: %PDF-
        if header_16.startswith(b"%PDF"):
            return "pdf"

        # OLE2 Compound Document (Legacy XLS): D0 CF 11 E0 A1 B1 1A E1
        if header_16.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            return "xls"

        # ZIP-based (XLSX / DOCX): PK\x03\x04
        if header_16.startswith(b"PK\x03\x04") or header_16.startswith(b"PK\x05\x06") or header_16.startswith(b"PK\x07\x08"):
            if ext in [".xlsx", ".xlsm", ".xltx", ".xltm"]:
                return "xlsx"
            if ext in [".docx", ".docm", ".dotx"]:
                return "docx"
            try:
                import zipfile
                import io
                zf = zipfile.ZipFile(file_bytes_or_path if isinstance(file_bytes_or_path, str) else io.BytesIO(file_bytes_or_path))
                namelist = zf.namelist()
                if any("xl/" in n for n in namelist) or "[Content_Types].xml" in namelist:
                    if any("workbook" in n.lower() for n in namelist):
                        return "xlsx"
                if any("word/" in n for n in namelist):
                    return "docx"
            except Exception:
                pass
            if ext in [".xlsx", ".xlsm"]:
                return "xlsx"
            if ext in [".docx"]:
                return "docx"

        # JSON detection: Starts with { or [
        sample_str = ""
        try:
            sample_str = header_bytes.decode("utf-8", errors="ignore").strip()
        except Exception:
            pass

        if sample_str:
            if (sample_str.startswith("{") and sample_str.endswith("}")) or (sample_str.startswith("[") and sample_str.endswith("]")) or ext == ".json":
                try:
                    import json
                    if isinstance(file_bytes_or_path, str):
                        with open(file_bytes_or_path, "r", encoding="utf-8") as f:
                            json.load(f)
                    else:
                        json.loads(file_bytes_or_path.decode("utf-8"))
                    return "json"
                except Exception:
                    if ext == ".json":
                        return "json"

        # Markdown detection
        if ext in [".md", ".markdown"]:
            return "md"

        # CSV detection
        if ext in [".csv", ".tsv"]:
            return "csv"

        if sample_str:
            lines = [l.strip() for l in sample_str.split("\n") if l.strip()]
            if len(lines) >= 2:
                comma_counts = [l.count(",") for l in lines[:5]]
                tab_counts = [l.count("\t") for l in lines[:5]]
                if comma_counts[0] >= 1 and all(c == comma_counts[0] for c in comma_counts):
                    return "csv"
                if tab_counts[0] >= 1 and all(t == tab_counts[0] for t in tab_counts):
                    return "csv"

        # Extension fallback for known extensions
        for fmt, cfg in SUPPORTED_FORMATS.items():
            if ext in cfg["extensions"]:
                return fmt

        # If MIME type is provided
        if mime_type:
            mime_clean = mime_type.lower().split(";")[0].strip()
            for fmt, cfg in SUPPORTED_FORMATS.items():
                if mime_clean in cfg["mimes"]:
                    return fmt

        # Plain text fallback if valid utf-8 string
        if sample_str and ext in [".txt", ".text", ".log"]:
            return "txt"

        supported_list = ", ".join([f"{k.upper()} ({', '.join(v['extensions'])})" for k, v in SUPPORTED_FORMATS.items()])
        raise UnsupportedFileFormatException(
            f"Unsupported file format '{ext or 'unknown'}' for file '{filename}'. "
            f"FinSight AI supports the following financial document formats: {supported_list}."
        )

    @staticmethod
    def validate_file(file_bytes_or_path: Union[bytes, str], filename: str, mime_type: Optional[str] = None) -> Tuple[str, int]:
        """
        Validates file size and format from bytes or file path without loading whole file into memory.
        Returns (format_type, file_size_bytes).
        """
        if isinstance(file_bytes_or_path, str):
            if not os.path.exists(file_bytes_or_path):
                raise UnsupportedFileFormatException(f"File '{filename}' does not exist.")
            file_size = os.path.getsize(file_bytes_or_path)
        else:
            file_size = len(file_bytes_or_path)

        if file_size == 0:
            raise UnsupportedFileFormatException(f"The uploaded file '{filename}' is empty (0 bytes).")

        fmt = FileTypeDetector.detect_format(file_bytes_or_path, filename, mime_type)

        max_limit = SUPPORTED_FORMATS.get(fmt, {}).get("max_size_bytes", 250 * 1024 * 1024)
        if file_size > max_limit:
            limit_mb = max_limit / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            raise UnsupportedFileFormatException(
                f"File '{filename}' ({actual_mb:.1f} MB) exceeds the maximum allowed size limit of {limit_mb:.0f} MB for {fmt.upper()} documents."
            )

        return fmt, file_size
