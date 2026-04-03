from app.extensions import db
from app.repositories.bank_version_repository import create_version, get_latest_version
from app.repositories.question_repository import create_question_entity


class BankVersionServiceError(Exception):
    pass


def create_new_version(bank_id: int, price: float, update_type: str):
    latest = get_latest_version(bank_id)
    next_number = 1 if latest is None else int(latest.version_number) + 1
    if update_type not in {"minor", "major"}:
        raise BankVersionServiceError("update_type must be 'minor' or 'major'.")
    try:
        version = create_version(
            bank_id=bank_id,
            version_number=next_number,
            price=float(price or 0.0),
            update_type=update_type,
        )
        version.is_major_update = update_type == "major"
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return version


def add_questions_to_version(version_id: int, questions_payload: list[dict]):
    created = []
    try:
        for item in questions_payload:
            question = create_question_entity(
                bank_version_id=version_id,
                bank_id=item.get("bank_id"),
                type=item.get("type"),
                content=item.get("content"),
                hint=item.get("hint"),
                points=float(item.get("points") or 1.0),
                base_time=item.get("base_time"),
                created_by=item.get("created_by"),
                original_question_id=item.get("original_question_id"),
            )
            created.append(question)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return created
