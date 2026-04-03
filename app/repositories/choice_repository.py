from app.extensions import db
from app.models import Choice


def delete_choices_by_question(question_id: int) -> None:
    Choice.query.filter_by(question_id=question_id).delete()


def create_choice(question_id: int, text: str, is_correct: bool) -> Choice:
    choice = Choice(
        question_id=question_id,
        text=text,
        is_correct=is_correct,
    )
    db.session.add(choice)
    db.session.flush()
    return choice
