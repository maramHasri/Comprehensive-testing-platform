"""
Quiz business logic: score recalculation (equally_weighted), publish validation,
create quiz from question bank.
"""
from app.extensions import db
from app.models import Quiz, Question, QuestionBank, Choice, QuestionAttribution
from app.models.question_bank import ACCESS_PUBLIC, ACCESS_PROTECTED, ACCESS_PRIVATE
from app.repositories.question_repository import get_questions_by_version
from app.services.question_bank.bank_access_service import get_user_accessible_version


def recalculate_question_scores(quiz: Quiz) -> None:
    """
    When quiz.equally_weighted is True, set every question's points to:
    question_score = total_score / number_of_questions
    Commits the session.
    """
    if not quiz.equally_weighted:
        return
    # Questions directly under this quiz (quiz_id = quiz.id)
    questions = Question.query.filter_by(quiz_id=quiz.id).order_by(Question.order_index).all()
    n = len(questions)
    if n == 0:
        return
    score_each = quiz.total_score / n
    for q in questions:
        q.points = score_each
    db.session.commit()


def validate_quiz_for_publish(quiz: Quiz) -> tuple[bool, str]:
    """
    Validate quiz integrity before publishing.
    Returns (True, "") if valid; (False, "error message") otherwise.
    Rules:
    - At least one question
    - All MCQ / True-False have at least one correct answer (and valid structure)
    - Total question score must match quiz total_score (when not equally_weighted we could allow sum == total_score)
    """
    questions = Question.query.filter_by(quiz_id=quiz.id).order_by(Question.order_index).all()
    if not questions:
        return False, "Quiz must have at least one question to be published."

    for q in questions:
        if q.type in ("mcq", "true_false"):
            correct = [c for c in q.choices if c.is_correct]
            if not correct:
                return False, f"Question (id={q.id}) must have at least one correct answer."
            if q.type == "true_false" and len(q.choices) != 2:
                return False, f"True/False question (id={q.id}) must have exactly two answers."
        if q.type == "essay" and q.choices:
            return False, f"Essay question (id={q.id}) must not have answers."

    # Total score check: when equally_weighted, we've already set points; otherwise sum must match
    total = sum(q.points for q in questions)
    if abs(total - quiz.total_score) > 0.01:  # float tolerance
        return False, f"Total question score ({total}) must match quiz total_score ({quiz.total_score})."

    return True, ""


def can_use_bank_for_quiz(bank: QuestionBank, current_user_id: int | None) -> bool:
    """True if the user can create a quiz from this bank (public/protected = any user; private = owner only)."""
    if current_user_id is None:
        return False
    if bank.access_type == ACCESS_PUBLIC or bank.access_type == ACCESS_PROTECTED:
        return True
    if bank.access_type == ACCESS_PRIVATE:
        return bank.owner_id == current_user_id
    return False


def create_quiz_from_bank(
    creator_id: int,
    bank_id: int,
    title: str,
    number_of_questions: int,
    description: str | None = None,
    total_score: int = 100,
    equally_weighted: bool = True,
    free_navigation: bool = True,
    timed_scope: str = "quiz",
    total_time_seconds: int | None = None,
) -> tuple[Quiz | None, str | None]:
    """
    Create a new quiz (draft) by copying questions and answers from a question bank.
    number_of_questions: how many questions to add (first N in bank order). Must be between 1 and bank size.
    Returns (quiz, None) on success, (None, error_message) on failure.
    """
    bank = QuestionBank.query.get(bank_id)
    if not bank:
        return None, "QUIZ_BANK_NOT_FOUND"
    if not can_use_bank_for_quiz(bank, creator_id):
        return None, "QUIZ_BANK_PERMISSION_DENIED"
    version = get_user_accessible_version(creator_id, bank.id)
    if version is None:
        return None, "QUIZ_BANK_PERMISSION_DENIED"
    bank_questions = get_questions_by_version(version.id)
    if not bank_questions:
        return None, "QUIZ_BANK_NO_QUESTIONS"
    if number_of_questions < 1:
        return None, "QUIZ_NUMBER_OF_QUESTIONS_MIN"
    if number_of_questions > len(bank_questions):
        return None, ("QUIZ_BANK_TOO_FEW_QUESTIONS", {"count": len(bank_questions)})
    if not title or not title.strip():
        return None, "QUIZ_TITLE_REQUIRED"

    # Use only the first N questions
    bank_questions = bank_questions[:number_of_questions]

    import uuid
    quiz = Quiz(
        title=title.strip(),
        description=description.strip() if description else None,
        creator_id=creator_id,
        total_score=float(total_score),
        equally_weighted=equally_weighted,
        free_navigation=free_navigation,
        timed_scope=timed_scope if timed_scope in ("quiz", "question", "none") else "quiz",
        total_time_seconds=total_time_seconds,
        status="draft",
        access_code=str(uuid.uuid4()),
    )
    db.session.add(quiz)
    db.session.flush()

    for order_index, bq in enumerate(bank_questions, start=1):
        new_q = Question(
            quiz_id=quiz.id,
            bank_id=None,
            type=bq.type,
            content=bq.content,
            created_by=bq.created_by,
            original_question_id=bq.original_question_id or bq.id,
            hint=bq.hint,
            points=bq.points,
            base_time=bq.base_time,
            order_index=order_index,
        )
        db.session.add(new_q)
        db.session.flush()
        if bq.created_by is not None:
            db.session.add(
                QuestionAttribution(
                    question_id=new_q.id,
                    original_question_id=bq.original_question_id or bq.id,
                    original_bank_id=bq.bank_id or bank.id,
                    original_owner_id=bq.created_by,
                )
            )
        for ch in bq.choices:
            new_c = Choice(
                question_id=new_q.id,
                text=ch.text,
                is_correct=ch.is_correct,
            )
            db.session.add(new_c)
    recalculate_question_scores(quiz)
    db.session.commit()
    return quiz, None
