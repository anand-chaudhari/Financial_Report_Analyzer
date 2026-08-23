import re
import unicodedata


def sanitize_filename(filename: str) -> str:
    """Sanitizes user uploaded filename to prevent directory traversal and special character issues."""
    filename = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")
    filename = re.sub(r"[^\w\s.-]", "", filename).strip()
    return re.sub(r"[-\s]+", "_", filename)


def format_file_size(size_in_bytes: int) -> str:
    """Formats file size in bytes to human-readable string (KB, MB, GB)."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} TB"
