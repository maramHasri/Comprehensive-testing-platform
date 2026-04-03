from app.extensions import db
from app.models import Quiz


def get_quiz_by_id(quiz_id: int):
    return Quiz.query.get(quiz_id)


def create_quiz(quiz):
    db.session.add(quiz)
    db.session.commit()
    return quiz


def get_all_quizzes():
    return Quiz.query.all()


def delete_quiz(quiz_id: int):
    quiz = Quiz.query.get(quiz_id)
    if quiz:
        db.session.delete(quiz)
        db.session.commit()
    return quiz