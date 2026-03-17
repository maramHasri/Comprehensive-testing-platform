"""
File processing service.

Detects file type and extracts text from:
- TXT
- DOCX
- PDF (text-based)
- Scanned PDF (via OCR: pdf2image + Tesseract).
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple


def detect_file_type(file_path: str) -> str:
    """
    Detect file type based on extension.
    Returns one of: 'txt', 'docx', 'pdf', 'unknown'.
    """
    ext = Path(file_path).suffix.lower()
    if ext == ".txt":
        return "txt"
    if ext == ".docx":
        return "docx"
    if ext == ".pdf":
        return "pdf"
    return "unknown"


def extract_text_from_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_text_from_docx(file_path: str) -> str:
    from docx import Document

    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs)


def _extract_pdf_text_based(file_path: str) -> str:
    from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    parts: list[str] = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        parts.append(txt)
    return "\n".join(parts).strip()


def extract_text_from_scanned_pdf(file_path: str) -> str:
    from pdf2image import convert_from_path
    import pytesseract

    # Configure Tesseract binary path for Windows
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    images = convert_from_path(file_path)
    parts: list[str] = []
    for img in images:
        txt = pytesseract.image_to_string(img)
        parts.append(txt)
    return "\n".join(parts).strip()


def extract_text_from_pdf(file_path: str) -> Tuple[str, str]:
    """
    Extract text from a PDF.

    Tries text-based extraction first; if result is too short, falls back to OCR.
    Returns (text, file_type) where file_type is 'pdf' or 'scanned_pdf'.
    """
    from app.utils.request_validation import trim_str

    text_pdf = _extract_pdf_text_based(file_path)
    if text_pdf and len(trim_str(text_pdf)) > 30:
        return text_pdf, "pdf"
    # Probably scanned → OCR
    text_ocr = extract_text_from_scanned_pdf(file_path)
    return text_ocr, "scanned_pdf"


def process_file(file_path: str) -> Tuple[str, str]:
    """
    Detect file type, extract text, and return (content_text, file_type_out).
    file_type_out is one of: 'txt', 'docx', 'pdf', 'scanned_pdf', 'unknown'.
    """
    ftype = detect_file_type(file_path)
    if ftype == "txt":
        return extract_text_from_txt(file_path), "txt"
    if ftype == "docx":
        return extract_text_from_docx(file_path), "docx"
    if ftype == "pdf":
        return extract_text_from_pdf(file_path)
    return "", "unknown"

