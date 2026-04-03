"""
HTTP-facing helpers for question answers (choices).
"""
from app.extensions import db
from app.models import Choice, Question
from app.services.quiz.question_service import update_question_answers as replace_all_answers


def get_answers(question_id: int):
    question = Question.query.get(question_id)
    if not question:
        return {"message": "Question not found."}, 404
    items = [
        {"id": c.id, "text": c.text, "is_correct": c.is_correct}
        for c in question.choices
    ]
    return items, 200


def add_single_answer(question_id: int, text: str, is_correct: bool):
    question = Question.query.get(question_id)
    if not question:
        return {"message": "Question not found."}, 404
    if not (text or "").strip():
        return {"message": "Answer text is required."}, 400
    if question.type == "essay":
        return {"message": "Essay questions cannot have answers."}, 400
    choice = Choice(
        question_id=question_id,
        text=text.strip(),
        is_correct=bool(is_correct),
    )
    db.session.add(choice)
    db.session.commit()
    return {
        "id": choice.id,
        "question_id": question_id,
        "text": choice.text,
        "is_correct": choice.is_correct,
    }, 201


def create_bulk_answers(question_id: int, answers: list[dict]):
    if not answers:
        return {"message": "No answers provided."}, 400
    try:
        created = replace_all_answers(question_id, answers)
    except ValueError as e:
        return {"message": str(e)}, 400
    return {
        "answers": [
            {"id": c.id, "text": c.text, "is_correct": c.is_correct}
            for c in created
        ]
    }, 200


def update_question_answers(question_id: int, answers_payload: list[dict]):
    created = replace_all_answers(question_id, answers_payload)
    return [
        {"id": c.id, "text": c.text, "is_correct": c.is_correct}
        for c in created
    ]
