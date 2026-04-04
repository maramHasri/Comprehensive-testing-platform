"""
AI quiz generation — JSON only. No file upload.

Pipeline:
  1. POST /api/extract-text  → { file_name, file_type, content_text }
  2. POST /api/ai/generate-quiz  → { "questions": [ ... ] }  (application/json)

Do not send files to /api/ai/generate-quiz; use step 1 first, then pass content_text in the body.
"""
from __future__ import annotations

import json

from flask import current_app, request
from flask_restx import Namespace, Resource, fields, reqparse

from app.services.ai_qwen_service import MAX_QUIZ_QUESTIONS
from app.services.generate_quiz_service import generate_quiz_from_text

ai_generation_ns = Namespace(
    " AI — Generate quiz (Qwen)",
    description="Step 2 only: generate questions from plain text via Hugging Face (Qwen). "
    "Requires content_text from POST /api/extract-text. Returns JSON with a questions array.",
)

generate_quiz_request_model = ai_generation_ns.model(
    "AiGenerateQuizRequest",
    {
        "content_text": fields.String(
            required=True,
            description="Plain text from POST /api/extract-text (required).",
        ),
        "question_type": fields.String(
            required=False,
            default="mixed",
            description="multiple-choice, true/false, short-answer, essay, mixed",
        ),
        "max_questions": fields.Integer(
            required=False,
            default=MAX_QUIZ_QUESTIONS,
            description=f"Clamped to 1–{MAX_QUIZ_QUESTIONS}",
        ),
    },
)

question_item_model = ai_generation_ns.model(
    "AiGeneratedQuestionItem",
    {
        "question": fields.String,
        "type": fields.String,
        "choices": fields.List(fields.String),
        "correct_answer": fields.String,
    },
)

quiz_json_response_model = ai_generation_ns.model(
    "AiGenerateQuizJsonResponse",
    {
        "questions": fields.List(fields.Nested(question_item_model)),
    },
)


def _merge_generate_quiz_body() -> dict:
    """JSON and form only — query allowed for testing; never read uploaded files."""
    merged: dict = {}
    merged.update(request.form.to_dict())
    merged.update(request.args.to_dict())
    body = request.get_json(silent=True)
    if isinstance(body, dict):
        merged.update(body)
    elif body is None and request.data:
        try:
            raw = json.loads(request.data.decode("utf-8-sig"))
            if isinstance(raw, dict):
                merged.update(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, AttributeError):
            pass
    if not merged.get("content_text"):
        forced = request.get_json(force=True, silent=True)
        if isinstance(forced, dict):
            merged.update(forced)
    return merged


@ai_generation_ns.route("/generate-quiz")
class AiGenerateQuiz(Resource):
    @ai_generation_ns.expect(generate_quiz_request_model, validate=False)
    @ai_generation_ns.response(200, "JSON: questions array only", quiz_json_response_model)
    @ai_generation_ns.response(400, "Validation error")
    @ai_generation_ns.response(502, "AI or parse failure")
    def post(self):
        """
        Generate quiz questions from **text only** (Qwen via Hugging Face).

        **Does not accept file uploads.** Use `/api/extract-text` first, then send `content_text` here.

        Success response shape (strict JSON):
        ```json
        { "questions": [ { "question", "type", "choices", "correct_answer" }, ... ] }
        ```
        """
        if request.files:
            for _k, f in request.files.items():
                if f and getattr(f, "filename", None):
                    return {
                        "message": "File upload is not allowed on this endpoint. "
                        "Use POST /api/extract-text to upload a file, then send content_text here.",
                        "questions": [],
                    }, 400

        merged = _merge_generate_quiz_body()
        content_text = merged.get("content_text")
        if content_text is None or (isinstance(content_text, str) and not content_text.strip()):
            return {
                "message": "content_text is required (non-empty string from POST /api/extract-text).",
                "questions": [],
            }, 400

        question_type = (merged.get("question_type") or "mixed").strip()
        max_q = merged.get("max_questions", MAX_QUIZ_QUESTIONS)
        try:
            max_questions = int(max_q) if max_q is not None else MAX_QUIZ_QUESTIONS
        except (TypeError, ValueError):
            max_questions = MAX_QUIZ_QUESTIONS

        body, status = generate_quiz_from_text(
            content_text=content_text if isinstance(content_text, str) else str(content_text),
            question_type=question_type,
            max_questions=max_questions,
        )
        return body, status
