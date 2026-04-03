# app/services/bank_service.py
from app.models import QuestionBank, Question, User, Choice
from app.extensions import db

class PermissionError(Exception): pass
class ValidationError(Exception): pass
class NotFoundError(Exception): pass

def get_current_user_id(jwt_identity):
    try:
        return int(jwt_identity) if jwt_identity else None
    except (TypeError, ValueError):
        return None

# ----- البنك -----
def create_bank(owner_id, title, access_type):
    from app.models.question_bank import ACCESS_PRIVATE, ACCESS_TYPES, ACCESS_PUBLIC
    if not title or not title.strip():
        raise ValidationError("Title is required")
    access_type = access_type.lower() if access_type else ACCESS_PRIVATE
    if access_type not in ACCESS_TYPES:
        access_type = ACCESS_PRIVATE
    bank = QuestionBank(
        title=title.strip(),
        owner_id=owner_id,
        access_type=access_type,
        is_public=(access_type == ACCESS_PUBLIC),
    )
    db.session.add(bank)
    db.session.commit()
    return bank

def update_bank(bank_id, owner_id, title=None, access_type=None):
    bank = QuestionBank.query.get(bank_id)
    if not bank:
        raise NotFoundError("Question bank not found")
    if bank.owner_id != owner_id:
        raise PermissionError("Only owner can update this bank")
    if title and title.strip():
        bank.title = title.strip()
    if access_type:
        access_type = access_type.lower()
        from app.models.question_bank import ACCESS_TYPES, ACCESS_PUBLIC
        if access_type in ACCESS_TYPES:
            bank.access_type = access_type
            bank.is_public = access_type == ACCESS_PUBLIC
    db.session.commit()
    return bank

def delete_bank(bank_id, owner_id):
    bank = QuestionBank.query.get(bank_id)
    if not bank:
        raise NotFoundError("Question bank not found")
    if bank.owner_id != owner_id:
        raise PermissionError("Only owner can delete")
    db.session.delete(bank)
    db.session.commit()
    return True

def get_bank(bank_id, current_user_id):
    bank = QuestionBank.query.get(bank_id)
    if not bank:
        raise NotFoundError("Bank not found")
    if not can_view_bank(bank, current_user_id):
        raise NotFoundError("Bank not visible")
    return bank

# ----- الأسئلة -----
def add_question_to_bank(bank_id, owner_id, payload):
    from app.routes.question_banks.service import create_question_with_answers
    bank = QuestionBank.query.get(bank_id)
    if not bank:
        raise NotFoundError("Bank not found")
    if bank.owner_id != owner_id:
        raise PermissionError("Only owner can add questions")
    return create_question_with_answers(bank_id, owner_id, payload)

def list_questions(bank_id, current_user_id):
    bank = get_bank(bank_id, current_user_id)
    return Question.query.filter_by(bank_id=bank.id).order_by(Question.id).all()


# ----- Helpers -----
def can_view_bank(bank, current_user_id):
    from app.models.question_bank import ACCESS_PUBLIC, ACCESS_PROTECTED, ACCESS_PRIVATE
    if bank.access_type in (ACCESS_PUBLIC, ACCESS_PROTECTED):
        return True
    if bank.access_type == ACCESS_PRIVATE:
        return bank.owner_id == current_user_id
    return False