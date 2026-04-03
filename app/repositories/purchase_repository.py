from app.extensions import db
from app.models import BankVersion, Purchase


def create_purchase(user_id: int, version_id: int, price_paid: float):
    version = BankVersion.query.get(version_id)
    purchase = Purchase(
        user_id=user_id,
        bank_id=version.bank_id if version else None,
        bank_version_id=version_id,
        price_paid=price_paid,
    )
    db.session.add(purchase)
    db.session.flush()
    return purchase


def get_user_purchases_for_bank(user_id: int, bank_id: int):
    return (
        Purchase.query.join(BankVersion, Purchase.bank_version_id == BankVersion.id)
        .filter(Purchase.user_id == user_id, BankVersion.bank_id == bank_id)
        .order_by(BankVersion.version_number.desc(), Purchase.id.desc())
        .all()
    )
