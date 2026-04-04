"""
Files — same extraction pipeline as POST /api/extract-text (shared file_processor).

Use either:
  - POST /api/extract-text  (recommended, step 1 of AI pipeline)
  - POST /api/files/extract_text  (alias, identical behaviour)
"""
import os
import tempfile
from pathlib import Path

from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from werkzeug.datastructures import FileStorage

from app.services.file_processor import process_file

files_ns = Namespace(
    " Files",
    description="Upload files (txt, pdf, docx) — same text extraction as /api/extract-text. "
    "For Qwen quiz generation use POST /api/ai/generate-quiz with content_text.",
)

extract_response_model = files_ns.model(
    "ExtractTextResponse",
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


@files_ns.route("/extract_text")
class ExtractText(Resource):
    @files_ns.expect(upload_parser)
    @files_ns.response(200, "Text extracted", extract_response_model)
    @files_ns.response(400, "Validation or extraction error")
    def post(self):
        """Upload a file and extract plain text (same logic as /api/extract-text)."""
        args = upload_parser.parse_args()
        upload = args.get("file")
        if not upload or not upload.filename:
            return {"message": "No file selected."}, 400

        original_name = upload.filename
        suffix = Path(original_name).suffix or ""
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                upload.save(tmp.name)
                tmp_path = tmp.name
            content_text, file_type_out = process_file(tmp_path)
            if not content_text:
                return {"message": "Failed to extract text from file."}, 400
            return {
                "file_name": original_name,
                "file_type": file_type_out,
                "content_text": content_text,
            }, 200
        except Exception:
            return {"message": "Failed to extract text from file."}, 400
        finally:
            if tmp_path and os.path.isfile(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
