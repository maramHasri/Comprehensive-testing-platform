from app.extensions import db
from app.models import QuestionBank, Question, Choice


def get_bank_by_id(bank_id: int) -> QuestionBank | None:
    return QuestionBank.query.get(bank_id)


def create_question(
    bank_id: int,
    text: str,
    qtype: str,
    points: float,
    base_time: int | None = None,
) -> Question:
    question = Question(
        bank_id=bank_id,
        type=qtype,
        content=text,
        points=points,
        base_time=base_time,
    )
    db.session.add(question)
    return question


def replace_question_answers(question: Question, answers_payload: list[dict]) -> list[Choice]:
    """
    Replace all answers (choices) for a question with the given payload.
    Does not commit; caller is responsible for transaction handling.
    """
    Choice.query.filter_by(question_id=question.id).delete()
    created: list[Choice] = []
    for a in answers_payload:
        choice = Choice(
            question_id=question.id,
            text=(a.get("text") or "").strip(),
            is_correct=bool(a.get("is_correct", False)),
        )
        db.session.add(choice)
        created.append(choice)
    return created

