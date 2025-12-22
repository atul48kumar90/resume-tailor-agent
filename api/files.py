# api/files.py
from fastapi import UploadFile
import pdfplumber
from docx import Document
import re
import os
from typing import IO


# ======================================================
# File Type Detection (Magic Bytes)
# ======================================================

def _detect_file_type(file_obj: IO) -> str:
    """
    Detect file type by reading magic bytes (file signature).
    More secure than relying on file extension.
    
    Returns:
        File type: 'pdf', 'docx', 'txt', or 'unknown'
    """
    current_pos = file_obj.tell()
    file_obj.seek(0)
    
    try:
        # Read first few bytes to detect file type
        header = file_obj.read(8)
        file_obj.seek(current_pos)  # Reset position
        
        if not header:
            return 'unknown'
        
        # PDF: starts with %PDF
        if header.startswith(b'%PDF'):
            return 'pdf'
        
        # DOCX: is a ZIP file (starts with PK\x03\x04)
        # DOCX files are ZIP archives containing XML
        if header.startswith(b'PK\x03\x04'):
            # Check if it's actually a DOCX by looking for word/ in the ZIP
            # For now, we'll trust the PK header and validate when opening
            return 'docx'
        
        # TXT: try to decode as UTF-8 (heuristic)
        try:
            header.decode('utf-8')
            # If it's mostly printable ASCII/UTF-8, likely text
            if all(32 <= b <= 126 or b in [9, 10, 13] for b in header[:7]):
                return 'txt'
        except (UnicodeDecodeError, ValueError):
            pass
        
        return 'unknown'
    except Exception:
        file_obj.seek(current_pos)
        return 'unknown'


def _validate_file_type(file_obj: IO, expected_type: str, filename: str) -> bool:
    """
    Validate that file content matches expected type.
    
    Args:
        file_obj: File object
        expected_type: Expected file type ('pdf', 'docx', 'txt')
        filename: Original filename for error messages
    
    Returns:
        True if file type matches, False otherwise
    
    Raises:
        ValueError: If file type doesn't match
    """
    detected_type = _detect_file_type(file_obj)
    
    if detected_type == 'unknown':
        raise ValueError(
            f"Could not detect file type for {filename}. "
            f"File may be corrupted or in an unsupported format."
        )
    
    if detected_type != expected_type:
        raise ValueError(
            f"File type mismatch for {filename}. "
            f"Extension suggests {expected_type}, but file content indicates {detected_type}. "
            f"Please ensure the file is actually a {expected_type} file."
        )
    
    return True


# ======================================================
# Public API
# ======================================================

def extract_text(file, max_size_bytes: int = None) -> str:
    """
    Accepts:
    - FastAPI UploadFile
    - File opened via open(...)
    
    Args:
        file: File object to extract text from
        max_size_bytes: Maximum file size in bytes (None = no limit)
    
    Returns:
        Extracted and normalized text
    
    Raises:
        ValueError: If file type is unsupported or file is too large
    """
    from core.settings import MAX_FILE_SIZE_BYTES
    
    if hasattr(file, "filename"):
        filename = file.filename.lower()
        file_obj = file.file
        # Check file size for UploadFile
        if hasattr(file, "size") and file.size:
            file_size = file.size
        else:
            # Read position to check size
            current_pos = file_obj.tell()
            file_obj.seek(0, 2)  # Seek to end
            file_size = file_obj.tell()
            file_obj.seek(current_pos)  # Reset position
    else:
        filename = os.path.basename(file.name).lower()
        file_obj = file
        # Check file size for regular file
        current_pos = file_obj.tell()
        file_obj.seek(0, 2)
        file_size = file_obj.tell()
        file_obj.seek(current_pos)

    max_size = max_size_bytes or MAX_FILE_SIZE_BYTES
    if file_size > max_size:
        raise ValueError(
            f"File size ({file_size / (1024*1024):.2f} MB) exceeds maximum allowed size "
            f"({max_size / (1024*1024):.2f} MB)"
        )

    # Determine expected file type from extension
    if filename.endswith(".pdf"):
        expected_type = "pdf"
        _validate_file_type(file_obj, "pdf", filename)
        text = _extract_pdf(file_obj)
    elif filename.endswith(".docx"):
        expected_type = "docx"
        _validate_file_type(file_obj, "docx", filename)
        text = _extract_docx(file_obj)
    elif filename.endswith(".txt"):
        expected_type = "txt"
        # For text files, we're more lenient (no magic bytes validation)
        text = _extract_txt(file_obj)
    else:
        raise ValueError(
            f"Unsupported file type: {filename}. "
            f"Supported formats: .pdf, .docx, .txt. "
            f"Please convert your file to one of these formats."
        )

    # 🔥 SINGLE SOURCE OF TRUTH - Use ATS normalization (lowercase for matching)
    return normalize_resume_text_for_ats(text)


# ======================================================
# PDF Extraction (ROBUST)
# ======================================================

def _extract_pdf(file_obj: IO) -> str:
    text_chunks = []

    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(
                x_tolerance=2,
                y_tolerance=2,
                layout=True,
            )
            if page_text:
                text_chunks.append(page_text)

    return "\n".join(text_chunks)


# ======================================================
# DOCX Extraction
# ======================================================

def _extract_docx(file_obj: IO) -> str:
    doc = Document(file_obj)
    return "\n".join(
        p.text for p in doc.paragraphs if p.text.strip()
    )


# ======================================================
# TXT Extraction
# ======================================================

def _extract_txt(file_obj: IO) -> str:
    return file_obj.read().decode("utf-8", errors="ignore")


# ======================================================
# Resume Normalization (MANDATORY)
# ======================================================

def normalize_resume_text(text: str, preserve_case: bool = False) -> str:
    """
    Repairs ATS-breaking artifacts introduced by PDF/DOCX extraction.
    This function MUST be applied before ATS scoring.
    
    Args:
        text: Raw text from PDF/DOCX extraction
        preserve_case: If True, preserves original case. If False, lowercases (for ATS matching)
    
    Returns:
        Normalized text ready for ATS scoring
    """
    if not text:
        return ""

    original_text = text
    if not preserve_case:
        text = text.lower()

    # --- Fix spaced letters (J a v a → java or Java)
    if preserve_case:
        # Preserve case but fix spacing
        text = re.sub(r'(?<!\w)([A-Za-z])\s+([A-Za-z])', lambda m: m.group(1) + m.group(2), text)
    else:
        text = re.sub(r'(?<!\w)([a-z])\s+([a-z])', r'\1\2', text)

    # --- Fix common ATS term fragmentation (case-insensitive)
    regex_replacements = {
        r'r\s*e\s*s\s*t': 'rest',
        r'a\s*p\s*i': 'api',
        r'h\s*t\s*t\s*p': 'http',
        r'j\s*s\s*o\s*n': 'json',
        r's\s*q\s*l': 'sql',
        r'k\s*u\s*b\s*e\s*r\s*n\s*e\s*t\s*e\s*s': 'kubernetes',
        r'd\s*o\s*c\s*k\s*e\s*r': 'docker',
    }

    for pattern, replacement in regex_replacements.items():
        if preserve_case:
            # Preserve original case of the matched text
            def replace_preserve_case(match):
                matched = match.group(0)
                if matched.isupper():
                    return replacement.upper()
                elif matched[0].isupper():
                    return replacement.capitalize()
                return replacement
            text = re.sub(pattern, replace_preserve_case, text, flags=re.I)
        else:
            text = re.sub(pattern, replacement, text, flags=re.I)

    # --- Normalize known resume patterns
    direct_replacements = {
        "ensuRESTability": "ensure rest stability",
        "http s": "http",
        "https": "http",
        "data structure & algorithm": "data structures algorithms",
        "data structure and algorithm": "data structures algorithms",
        "distributed system": "distributed systems",
        "highly available solutions": "high availability",
        "code review & optimization": "code review optimization",
    }

    for src, tgt in direct_replacements.items():
        if preserve_case:
            # Case-insensitive replacement but preserve surrounding case
            text = re.sub(re.escape(src), tgt, text, flags=re.I)
        else:
            text = text.replace(src.lower(), tgt)

    # --- Normalize bullets & separators
    text = text.replace("•", " ").replace("●", " ").replace("▪", " ")
    text = text.replace("|", " ").replace("-", " ")

    # --- Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_resume_text_for_ats(text: str) -> str:
    """
    Normalizes text specifically for ATS scoring (lowercase).
    Use this when you need case-insensitive matching.
    """
    return normalize_resume_text(text, preserve_case=False)


def normalize_resume_text_preserve_case(text: str) -> str:
    """
    Normalizes text while preserving original case.
    Use this when you need to display or export the text.
    """
    return normalize_resume_text(text, preserve_case=True)
