# api/files.py
from fastapi import UploadFile
import pdfplumber
from docx import Document
import re
import os
from typing import IO


# ======================================================
# Public API
# ======================================================

def extract_text(file) -> str:
    """
    Accepts:
    - FastAPI UploadFile
    - File opened via open(...)
    """
    if hasattr(file, "filename"):
        filename = file.filename.lower()
        file_obj = file.file
    else:
        filename = os.path.basename(file.name).lower()
        file_obj = file

    if filename.endswith(".pdf"):
        text = _extract_pdf(file_obj)
    elif filename.endswith(".docx"):
        text = _extract_docx(file_obj)
    elif filename.endswith(".txt"):
        text = _extract_txt(file_obj)
    else:
        raise ValueError("Unsupported file type")

    # 🔥 SINGLE SOURCE OF TRUTH
    return normalize_resume_text(text)


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

def normalize_resume_text(text: str) -> str:
    """
    Repairs ATS-breaking artifacts introduced by PDF/DOCX extraction.
    This function MUST be applied before ATS scoring.
    """
    if not text:
        return ""

    text = text.lower()

    # --- Fix spaced letters (J a v a → java)
    text = re.sub(r'(?<!\w)([a-z])\s+([a-z])', r'\1\2', text)

    # --- Fix common ATS term fragmentation
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
        text = text.replace(src.lower(), tgt)

    # --- Normalize bullets & separators
    text = text.replace("•", " ").replace("●", " ").replace("▪", " ")
    text = text.replace("|", " ").replace("-", " ")

    # --- Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()
