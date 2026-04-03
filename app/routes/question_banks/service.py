from typing import Any, Dict

from app.extensions import db
from app.routes.question_banks.repository import (
    get_bank_by_id,
    create_question,
    replace_question_answers,
)
from app.repositories.bank_version_repository import get_latest_version
from app.services.question_bank.bank_version_service import create_new_version


class ValidationError(Exception):
    pass


class PermissionError(Exception):
    pass


class NotFoundError(Exception):
    pass


ALLOWED_QTYPES = {"mcq", "true_false", "essay"}
QTYPE_ALIASES = {
    "multiple_choice": "mcq",
    "multiple-choice": "mcq",
    "true/false": "true_false",
    "true-false": "true_false",
}


def _validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")

    text = (payload.get("text") or "").strip()
    if not text:
        raise ValidationError("Field 'text' is required.")

    # Support both "question_type" (new JSON API) and "type" (backwards compatibility)
    qtype_raw = (
        (payload.get("question_type") or payload.get("type") or "")
        .strip()
        .lower()
    )
    qtype = QTYPE_ALIASES.get(qtype_raw, qtype_raw)
    if qtype not in ALLOWED_QTYPES:
        raise ValidationError("Invalid question_type. Allowed: mcq, true_false, essay.")

    answers = payload.get("answers")
    if answers is not None:
        if not isinstance(answers, list):
            raise ValidationError("Field 'answers' must be a list if provided.")
        if not answers:
            raise ValidationError("If 'answers' is provided, it must not be empty.")
        if qtype == "essay":
            raise ValidationError("Essay questions must not have answers.")

        has_correct = any(bool(a.get("is_correct")) for a in answers)
        if not has_correct:
            raise ValidationError("At least one answer must be marked as correct.")

        for idx, ans in enumerate(answers):
            if not isinstance(ans, dict):
                raise ValidationError(f"Answer at index {idx} must be an object.")
            if not (ans.get("text") or "").strip():
                raise ValidationError(f"Answer at index {idx} is missing 'text'.")

    return {
        "text": text,
        "question_type": qtype,
        "answers": answers,
    }


def _question_to_dict(question) -> Dict[str, Any]:
    return {
        "id": question.id,
        "bank_id": question.bank_id,
        "type": question.type,
        "content": question.content,
        "created_by": question.created_by,
        "original_question_id": question.original_question_id,
        "points": question.points,
        "base_time": question.base_time,
        "answers": [
            {"id": c.id, "text": c.text, "is_correct": c.is_correct}
            for c in question.choices
        ],
    }


def create_question_with_answers(
    bank_id: int,
    owner_id: int,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a question in a bank, optionally with answers, in a single transaction.
    """
    bank = get_bank_by_id(bank_id)
    if not bank:
        raise NotFoundError("Question bank not found.")
    if bank.owner_id != owner_id:
        raise PermissionError("Only the owner can edit or delete this question bank.")

    data = _validate_payload(payload)
    text = data["text"]
    qtype = data["question_type"]
    answers = data["answers"]

    points = float(payload.get("points") or payload.get("score") or 1.0)
    base_time = payload.get("time_limit_seconds")
    original_question_id = payload.get("original_question_id")

    try:
        latest_version = get_latest_version(bank.id)
        if latest_version is None:
            create_new_version(
                bank_id=bank.id,
                price=float(getattr(bank, "base_price", 0.0) or 0.0),
                update_type="major" if getattr(bank, "is_paid", False) else "minor",
            )
        question = create_question(
            bank_id=bank.id,
            text=text,
            qtype=qtype,
            points=points,
            created_by=owner_id,
            original_question_id=original_question_id,
            base_time=base_time,
        )
        if answers:
            replace_question_answers(question, answers)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return _question_to_dict(question)

