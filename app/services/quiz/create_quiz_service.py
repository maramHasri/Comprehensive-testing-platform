"""
Quiz creation from bank — API layer with localized messages (message_key + lang).
Calls core domain logic in app.services.quiz_service (shim to quiz.quiz_service).
"""
from app.localization.message_service import get_message, get_message_format
from app.services.quiz.quiz_service import create_quiz_from_bank as _create_quiz_from_bank_core
from app.utils.localization import get_current_lang


def create_quiz_from_bank(
    creator_id: int,
    bank_id: int,
    title: str,
    number_of_questions,
    description: str | None = None,
    total_score: int = 100,
    equally_weighted: bool = True,
    free_navigation: bool = True,
    timed_scope: str = "quiz",
    total_time_seconds: int | None = None,
    lang: str | None = None,
) -> tuple[dict, int]:
    """
    Returns (response_dict, status_code). All user-facing messages localized.
    """
    if lang is None:
        lang = get_current_lang()
    title = (title or "").strip()
    if not title:
        return {"message": get_message("QUIZ_TITLE_REQUIRED", lang)}, 400
    try:
        total_score = int(total_score) if total_score is not None else 100
    except (TypeError, ValueError):
        total_score = 100
    if total_score <= 0:
        return {"message": get_message("QUIZ_TOTAL_SCORE_INVALID", lang)}, 400
    if number_of_questions is None:
        return {"message": get_message("QUIZ_NUMBER_OF_QUESTIONS_REQUIRED", lang)}, 400
    try:
        number_of_questions = int(number_of_questions)
    except (TypeError, ValueError):
        return {"message": get_message("QUIZ_NUMBER_OF_QUESTIONS_INVALID", lang)}, 400
    if number_of_questions < 1:
        return {"message": get_message("QUIZ_NUMBER_OF_QUESTIONS_MIN", lang)}, 400

    quiz, err = _create_quiz_from_bank_core(
        creator_id=creator_id,
        bank_id=bank_id,
        title=title,
        number_of_questions=number_of_questions,
        description=description,
        total_score=total_score,
        equally_weighted=equally_weighted,
        free_navigation=free_navigation,
        timed_scope=(timed_scope or "quiz").lower(),
        total_time_seconds=total_time_seconds,
    )
    if err:
        if isinstance(err, tuple):
            key, fmt_kwargs = err
            msg = get_message_format(key, lang, **fmt_kwargs)
        else:
            msg = get_message(err, lang)
        err_key = err[0] if isinstance(err, tuple) else err
        if err_key == "QUIZ_BANK_NOT_FOUND":
            return {"message": msg}, 404
        return {"message": msg}, 400
    return {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "status": quiz.status,
        "access_code": quiz.access_code,
        "quiz_url": f"http://localhost:5000/quiz/{quiz.access_code}",
        "total_score": int(quiz.total_score),
        "equally_weighted": quiz.equally_weighted,
        "free_navigation": quiz.free_navigation,
        "timed_scope": quiz.timed_scope,
    }, 201
