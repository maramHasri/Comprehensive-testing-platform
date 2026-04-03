"""Question repository facade."""
from app.models import Question
from app.repositories.question import create_question_entity, get_question_by_id


def get_questions_by_version(version_id: int):
    return (
        Question.query.filter_by(bank_version_id=version_id)
        .order_by(Question.id.asc())
        .all()
    )


__all__ = ["create_question_entity", "get_question_by_id", "get_questions_by_version"]
