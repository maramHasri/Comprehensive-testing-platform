from app.repositories.question_repository import get_question_by_id
from app.services.quiz.answer_service import (
    replace_question_answers,
    validate_answers,
)
from app.extensions import db


def update_question_answers(question_id: int, answers_payload: list[dict]):
    question = get_question_by_id(question_id)

    validate_answers(question, answers_payload)

    created = replace_question_answers(question_id, answers_payload)

    db.session.commit()

    return created