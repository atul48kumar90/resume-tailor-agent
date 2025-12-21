# api/files.py
from fastapi import UploadFile
from pypdf import PdfReader
from docx import Document


def extract_text(file: UploadFile) -> str:
    filename = file.filename.lower()

    if filename.endswith(".pdf"):
        return _extract_pdf(file)

    if filename.endswith(".docx"):
        return _extract_docx(file)

    if filename.endswith(".txt"):
        return _extract_txt(file)

    raise ValueError("Unsupported file type")


def _extract_pdf(file: UploadFile) -> str:
    reader = PdfReader(file.file)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(file: UploadFile) -> str:
    doc = Document(file.file)
    return "\n".join(p.text for p in doc.paragraphs)


def _extract_txt(file: UploadFile) -> str:
    return file.file.read().decode("utf-8")
