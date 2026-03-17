"""
Shared logic for creating answers (bulk). Used by question API and question_bank API.
"""
from app.extensions import db
from app.models import Question, Choice


def create_bulk_answers(question, answers_payload):
    """
    Validate and create bulk answers for a question. Replaces existing choices.
    Returns (response_dict, status_code) on success, (error_dict, 400) on validation error.
    question: Question model instance.
    answers_payload: list of {"text": str, "is_correct": bool}.
    """
    if question.type == "essay":
        return {"message": "Essay questions must not have answers."}, 400

    if question.type not in ("mcq", "true_false"):
        return {"message": "Bulk answers are only supported for MCQ and True/False questions."}, 400

    if not answers_payload:
        return {"message": "At least one answer is required."}, 400

    correct_count = sum(1 for a in answers_payload if a.get("is_correct"))
    if correct_count == 0:
        return {"message": "At least one answer must be marked as correct."}, 400

    if correct_count > 1:
        return {"message": "Only one answer can be marked as correct for this question type."}, 400

    if question.type == "true_false" and len(answers_payload) != 2:
        return {"message": "True/False question must have exactly two answers."}, 400

    if any(not (a.get("text") or "").strip() for a in answers_payload):
        return {"message": "Every answer must have non-empty text."}, 400

    Choice.query.filter_by(question_id=question.id).delete()
    created = []
    for a in answers_payload:
        choice = Choice(
            question_id=question.id,
            text=(a.get("text") or "").strip(),
            is_correct=bool(a.get("is_correct", False)),
        )
        db.session.add(choice)
        created.append(choice)
    db.session.commit()

    return {
        "question_id": question.id,
        "answers": [{"id": c.id, "text": c.text, "is_correct": c.is_correct} for c in created],
    }, 201
