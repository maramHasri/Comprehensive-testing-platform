"""
Processing — step 1 only: file → plain text.

Step 2 (AI quiz JSON): POST /api/ai/generate-quiz with `content_text` from this endpoint.

Pipeline:
  1. POST /api/extract-text  → { file_name, file_type, content_text }
  2. POST /api/ai/generate-quiz  → { "questions": [ ... ] }
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from flask_restx import Namespace, Resource, fields, reqparse
from werkzeug.datastructures import FileStorage

from app.services.file_processor import process_file

processing_ns = Namespace(
    " Processing — Extract text",
    description="Upload a file and get plain text only. For AI quiz generation, call POST /api/ai/generate-quiz next.",
)

extract_response_model = processing_ns.model(
    "ProcessingExtractTextResponse",
    {
        "file_name": fields.String,
        "file_type": fields.String,
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


@processing_ns.route("/extract-text")
class ExtractText(Resource):
    @processing_ns.expect(upload_parser)
    @processing_ns.response(200, "Text extracted", extract_response_model)
    @processing_ns.response(400, "Validation or extraction error")
    def post(self):
        """Upload a file and extract plain text (TXT, DOCX, PDF, scanned PDF). Then use /api/ai/generate-quiz."""
        args = upload_parser.parse_args()
        upload = args.get("file")
        if not upload or not upload.filename:
            return {"message": "No file selected."}, 400

        suffix = Path(upload.filename).suffix or ""
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                upload.save(tmp.name)
                tmp_path = tmp.name
            content_text, file_type = process_file(tmp_path)
            if not content_text:
                return {"message": "Failed to extract text from file."}, 400
            return {
                "file_name": upload.filename,
                "file_type": file_type,
                "content_text": content_text,
            }, 200
        finally:
            if tmp_path and os.path.isfile(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
