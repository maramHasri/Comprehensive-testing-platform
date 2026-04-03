def validate_create_quiz_input(title, number_of_questions, total_score):
    if not (title or "").strip():
        return "QUIZ_TITLE_REQUIRED"

    try:
        total_score = int(total_score) if total_score is not None else 100
    except:
        total_score = 100

    if total_score <= 0:
        return "QUIZ_TOTAL_SCORE_INVALID"

    if number_of_questions is None:
        return "QUIZ_NUMBER_OF_QUESTIONS_REQUIRED"

    try:
        number_of_questions = int(number_of_questions)
    except:
        return "QUIZ_NUMBER_OF_QUESTIONS_INVALID"

    if number_of_questions < 1:
        return "QUIZ_NUMBER_OF_QUESTIONS_MIN"

    return None