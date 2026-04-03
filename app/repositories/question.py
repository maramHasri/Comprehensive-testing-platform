from app.models import Question
from app.extensions import db


def create_question_entity(**kwargs) -> Question:
    question = Question(**kwargs)
    db.session.add(question)
    db.session.flush()
    return question


def get_question_by_id(question_id: int):
    return Question.query.get(question_id)