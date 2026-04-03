"""
Files — upload educational files and extract plain text for Gemini question generation.
Supports TXT, DOCX, PDF (text-based) and scanned PDF (OCR).
"""
# TODO: Move extraction/business workflow to services/question_service.py (or dedicated file_service.py).
# TODO: Keep this file as route layer only in app/api/question_routes.py style.
from pathlib import Path
import tempfile

from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from werkzeug.datastructures import FileStorage

from app.utils.request_validation import trim_str


files_ns = Namespace(
    " Files",
    description="Upload files (txt, pdf, docx) and extract plain text for question generation.",
)


extract_response_model = files_ns.model(
    "ExtractTextResponse",
    {
        "file_name": fields.String,
        "file_type": fields.String,  # txt | pdf | scanned_pdf | docx | unknown
        "content_text": fields.String,
    },
)


upload_parser = reqparse.RequestParser()
upload_parser.add_argument(
    "file",
    type=FileStorage,
    location="files",
    required=True,
    help="File to upload (txt, pdf, docx)",
)

def _detect_type_from_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".txt":
        return "txt"
    if ext == ".docx":
        return "docx"
    if ext == ".pdf":
        return "pdf"
    return "unknown"


def _extract_text_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _extract_text_docx(path: str) -> str:
    from docx import Document

    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def _extract_text_pdf_text(path: str) -> str:
    from PyPDF2 import PdfReader

    reader = PdfReader(path)
    parts: list[str] = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        parts.append(txt)
    return "\n".join(parts).strip()


def _extract_text_pdf_ocr(path: str) -> str:
    from pdf2image import convert_from_path
    import pytesseract

    images = convert_from_path(path)
    parts: list[str] = []
    for img in images:
        txt = pytesseract.image_to_string(img)
        parts.append(txt)
    return "\n".join(parts).strip()


@files_ns.route("/extract_text")
class ExtractText(Resource):
    @files_ns.expect(upload_parser)
    @files_ns.response(200, "Text extracted", extract_response_model)
    @files_ns.response(400, "Validation or extraction error")
    def post(self):
        """
        Upload a file and extract plain text.

        The response is ready to be sent to Gemini:
        {
          "file_name": ...,
          "file_type": "txt|pdf|scanned_pdf|docx",
          "content_text": "full extracted text"
        }
        """
        if "file" not in request.files:
            return {"message": "No file part in the request."}, 400

        upload = request.files["file"]
        if not upload or not upload.filename:
            return {"message": "No file selected."}, 400

        original_name = upload.filename
        detected = _detect_type_from_extension(original_name)

        suffix = Path(original_name).suffix or ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            upload.save(tmp.name)
            tmp_path = tmp.name

        try:
            file_type_out = detected
            content_text = ""

            if detected == "txt":
                content_text = _extract_text_txt(tmp_path)
            elif detected == "docx":
                content_text = _extract_text_docx(tmp_path)
            elif detected == "pdf":
                # Try text-based first
                text_pdf = _extract_text_pdf_text(tmp_path)
                if text_pdf and len(trim_str(text_pdf)) > 30:
                    content_text = text_pdf
                    file_type_out = "pdf"
                else:
                    content_text = _extract_text_pdf_ocr(tmp_path)
                    file_type_out = "scanned_pdf"
            else:
                return {"message": "Unsupported file type."}, 400

            return {
                "file_name": original_name,
                "file_type": file_type_out,
                "content_text": content_text or "",
            }, 200
        except Exception:
            return {"message": "Failed to extract text from file."}, 400

