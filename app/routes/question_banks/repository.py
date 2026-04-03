from app.extensions import db
from app.models import QuestionBank, Question, Choice, BankQuestion, QuestionAttribution
from app.repositories.bank_version_repository import get_latest_version


def get_bank_by_id(bank_id: int) -> QuestionBank | None:
    return QuestionBank.query.get(bank_id)


def create_question(
    bank_id: int,
    text: str,
    qtype: str,
    points: float,
    created_by: int | None = None,
    original_question_id: int | None = None,
    base_time: int | None = None,
) -> Question:
    latest_version = get_latest_version(bank_id)
    question = Question(
        bank_id=bank_id,
        bank_version_id=latest_version.id if latest_version else None,
        type=qtype,
        content=text,
        points=points,
        created_by=created_by,
        original_question_id=original_question_id,
        base_time=base_time,
    )
    db.session.add(question)
    db.session.flush()

    db.session.add(
        BankQuestion(
            bank_id=bank_id,
            question_id=question.id,
        )
    )

    source_question_id = original_question_id or question.id
    source_question = Question.query.get(source_question_id)
    original_bank_id = source_question.bank_id if source_question else bank_id
    original_owner_id = source_question.created_by if source_question and source_question.created_by else created_by

    if original_owner_id is not None:
        db.session.add(
            QuestionAttribution(
                question_id=question.id,
                original_question_id=source_question_id,
                original_bank_id=original_bank_id,
                original_owner_id=original_owner_id,
            )
        )
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

