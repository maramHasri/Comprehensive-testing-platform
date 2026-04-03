

from app.repositories.choice_repository import (
    delete_choices_by_question,
    create_choice
)


def validate_answers(question, answers_payload):
    if question.type == "essay":
        raise ValueError("Essay questions cannot have answers.")

    if question.type not in ("mcq", "true_false"):
        raise ValueError("Unsupported question type.")

    if not answers_payload:
        raise ValueError("At least one answer is required.")

    correct_count = sum(1 for a in answers_payload if a.get("is_correct"))

    if correct_count == 0:
        raise ValueError("At least one correct answer required.")

    if correct_count > 1:
        raise ValueError("Only one correct answer allowed.")

    if question.type == "true_false" and len(answers_payload) != 2:
        raise ValueError("True/False must have exactly two answers.")

    if any(not (a.get("text") or "").strip() for a in answers_payload):
        raise ValueError("All answers must have text.")


def replace_question_answers(question_id: int, answers_payload: list[dict]):
    delete_choices_by_question(question_id)

    created = []

    for a in answers_payload:
        choice = create_choice(
            question_id=question_id,
            text=(a.get("text") or "").strip(),
            is_correct=bool(a.get("is_correct", False)),
        )
        created.append(choice)

    return created