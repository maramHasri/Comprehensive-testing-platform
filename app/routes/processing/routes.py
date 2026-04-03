"""
Processing API — file extraction + Gemini quiz generation.

Endpoints:
- POST /api/extract-text
- POST /api/generate-quiz
"""
# TODO: This API module orchestrates multiple domain services and response shaping.
# TODO: Move non-HTTP business logic to services/question_service.py and services/bank_service.py.
from __future__ import annotations

import tempfile
from pathlib import Path

from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from werkzeug.datastructures import FileStorage

from app.services.file_processor import process_file
from app.services.ai_qwen_service import generate_questions


processing_ns = Namespace(
    " Processing",
    description="File processing and quiz generation using Qwen.",
)


extract_response_model = processing_ns.model(
    "ProcessingExtractTextResponse",
    {
        "file_name": fields.String,
        "file_type": fields.String,
        "content_text": fields.String,
    },
)


quiz_response_model = processing_ns.model(
    "GenerateQuizResponse",
    {
        "file_name": fields.String,
        "file_type": fields.String,
        "questions": fields.List(fields.Raw),
        "raw": fields.String(description="Model output when JSON shape unexpected or for debugging"),
        "error": fields.String(description="Parse error message if model did not return valid JSON"),
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

quiz_parser = upload_parser.copy()
quiz_parser.add_argument(
    "question_type",
    type=str,
    location="form",
    required=True,
    help="Question type: multiple-choice, true/false, short-answer, essay, mixed",
)
quiz_parser.add_argument(
    "max_questions",
    type=int,
    location="form",
    required=True,
    help="Maximum number of questions to generate",
)


@processing_ns.route("/extract-text")
class ExtractText(Resource):
    @processing_ns.expect(upload_parser)
    @processing_ns.response(200, "Text extracted", extract_response_model)
    @processing_ns.response(400, "Validation or extraction error")
    def post(self):
        """Upload a file and extract plain text (TXT, DOCX, PDF, scanned PDF)."""
        args = upload_parser.parse_args()
        upload = args.get("file")
        if not upload or not upload.filename:
            return {"message": "No file selected."}, 400

        suffix = Path(upload.filename).suffix or ""
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


@processing_ns.route("/generate-quiz")
class GenerateQuiz(Resource):
    @processing_ns.expect(quiz_parser)
    @processing_ns.response(200, "Quiz generated", quiz_response_model)
    @processing_ns.response(400, "Validation or extraction error")
    @processing_ns.response(502, "AI generation error")
    def post(self):
        """
        Full pipeline:
        1. Upload file
        2. Extract text
        3. Send text to Gemini
        4. Return generated questions
        """
        args = quiz_parser.parse_args()
        upload = args.get("file")
        if not upload or not upload.filename:
            return {"message": "No file selected."}, 400

        question_type = (args.get("question_type") or "").strip() or "mixed"
        max_questions = args.get("max_questions") or 10
        # Prevent overly large outputs that would truncate the model response.
        max_questions = max(1, min(int(max_questions), 10))

        suffix = Path(upload.filename).suffix or ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            upload.save(tmp.name)
            tmp_path = tmp.name

        content_text, file_type = process_file(tmp_path)
        if not content_text:
            return {"message": "Failed to extract text from file."}, 400

        try:
            questions_payload = generate_questions(
                text=content_text,
                question_type=question_type,
                max_questions=max_questions,
            )
        except Exception as e:
            # Return a clear JSON error instead of HTML 500
            return {
                "message": "AI question generation failed.",
                "error": str(e),
            }, 502

        questions = questions_payload.get("questions", [])
        out = {
            "file_name": upload.filename,
            "file_type": file_type,
            "questions": questions,
        }
        if "raw" in questions_payload:
            out["raw"] = questions_payload.get("raw")
        if "error" in questions_payload:
            out["error"] = questions_payload.get("error")
        return out, 200

