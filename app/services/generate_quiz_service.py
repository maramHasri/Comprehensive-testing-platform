"""
Generate quiz questions from plain text via Qwen (Hugging Face) — no file I/O.

Pipeline:
  1. POST /api/extract-text → content_text
  2. POST /api/ai/generate-quiz → JSON { "questions": [ ... ] }
"""
from __future__ import annotations

from typing import Any

from flask import current_app

from app.services.ai_qwen_service import MAX_QUIZ_QUESTIONS, generate_questions


def _normalize_question_items(items: list[Any]) -> list[dict[str, Any]]:
    """Ensure each item is a plain dict suitable for JSON (no ORM / extra keys)."""
    out: list[dict[str, Any]] = []
    for q in items:
        if not isinstance(q, dict):
            continue
        choices = q.get("choices")
        if not isinstance(choices, list):
            choices = []
        choices = [str(c) for c in choices if c is not None]
        out.append(
            {
                "question": str(q.get("question", "") or ""),
                "type": str(q.get("type", "multiple-choice") or "multiple-choice"),
                "choices": choices,
                "correct_answer": str(q.get("correct_answer", "") or ""),
            }
        )
    return out


def generate_quiz_from_text(
    content_text: str,
    question_type: str,
    max_questions: int,
) -> tuple[dict, int]:
    """
    AI generation only. Returns (response_body, http_status).

    Success (200): strictly ``{"questions": [...]}`` — valid JSON-friendly dicts only.
    Failure (502): ``{"message": str, "questions": []}`` — no raw model dump unless debug.
    """
    text = (content_text or "").strip()
    if not text:
        return {"message": "content_text is required and must not be empty.", "questions": []}, 400

    qtype = (question_type or "").strip() or "mixed"
    try:
        n = int(max_questions)
    except (TypeError, ValueError):
        n = MAX_QUIZ_QUESTIONS
    n = max(1, min(n, MAX_QUIZ_QUESTIONS))

    try:
        questions_payload = generate_questions(
            text=text,
            question_type=qtype,
            max_questions=n,
        )
    except Exception as e:
        return {
            "message": "AI question generation failed.",
            "questions": [],
            "error": str(e),
        }, 502

    raw_list = questions_payload.get("questions", [])
    if not isinstance(raw_list, list):
        raw_list = []

    normalized = _normalize_question_items(raw_list)
    debug = bool(current_app and current_app.debug)

    if normalized:
        body: dict = {"questions": normalized}
        if debug and questions_payload.get("raw"):
            body["_debug_raw"] = questions_payload.get("raw")
        return body, 200

    # Model returned no usable questions
    err_msg = questions_payload.get("error") or "Model did not return valid JSON questions."
    body = {"message": err_msg, "questions": []}
    if debug:
        if questions_payload.get("error"):
            body["error"] = questions_payload["error"]
        if questions_payload.get("raw"):
            body["_debug_raw"] = (questions_payload.get("raw") or "")[:2000]
    return body, 502
