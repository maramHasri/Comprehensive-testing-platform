from app.extensions import db
from app.models import QuestionBank, BankVersion, Purchase
from app.services.bank_pricing_service import calculate_price, can_be_paid


class BankVersionError(Exception):
    pass


def create_bank_version(
    bank_id: int,
    version_number: str,
    question_count: int,
    topic_count: int,
    is_major_update: bool,
):
    bank = QuestionBank.query.get(bank_id)
    if not bank:
        raise BankVersionError("Question bank not found.")

    version = BankVersion(
        bank_id=bank_id,
        version_number=(version_number or "").strip(),
        question_count=int(question_count or 0),
        topic_count=int(topic_count or 0),
        is_major_update=bool(is_major_update),
    )

    if bank.is_paid and not can_be_paid(version):
        raise BankVersionError(
            "Paid bank versions require at least 100 questions and 2 topics."
        )

    db.session.add(version)
    db.session.commit()
    return version


def purchase_bank_version(user, bank_id: int, version_id: int):
    bank = QuestionBank.query.get(bank_id)
    if not bank:
        raise BankVersionError("Question bank not found.")

    version = BankVersion.query.filter_by(id=version_id, bank_id=bank_id).first()
    if not version:
        raise BankVersionError("Bank version not found.")

    if not version.is_major_update:
        raise BankVersionError("Only major updates are purchasable versions.")

    price = calculate_price(user=user, bank=bank, version=version)
    purchase = Purchase(
        user_id=user.id,
        bank_id=bank.id,
        bank_version_id=version.id,
        price_paid=price,
    )
    db.session.add(purchase)
    db.session.commit()
    return purchase
