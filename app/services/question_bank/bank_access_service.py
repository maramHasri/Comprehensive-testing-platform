from app.extensions import db
from app.repositories.bank_version_repository import (
    get_latest_version,
    get_version_by_id,
)
from app.repositories.purchase_repository import (
    create_purchase,
    get_user_purchases_for_bank,
)


class BankAccessError(Exception):
    pass


def get_user_accessible_version(user_id: int, bank_id: int):
    latest = get_latest_version(bank_id)
    if latest is None:
        return None
    if latest.update_type == "minor":
        return latest
    purchases = get_user_purchases_for_bank(user_id, bank_id) if user_id else []
    if not purchases:
        return None
    return get_version_by_id(purchases[0].bank_version_id)


def can_upgrade(user_id: int, bank_id: int) -> bool:
    latest = get_latest_version(bank_id)
    current = get_user_accessible_version(user_id, bank_id)
    if latest is None or current is None:
        return False
    return latest.version_number > current.version_number


def calculate_upgrade_price(user_id: int, bank_id: int) -> float:
    latest = get_latest_version(bank_id)
    current = get_user_accessible_version(user_id, bank_id)
    if latest is None:
        raise BankAccessError("Latest version not found.")
    if current is None:
        return max(float(latest.price or 0.0), 0.0)
    return max(float(latest.price or 0.0) - float(current.price or 0.0), 0.0)


def upgrade_bank(user_id: int, bank_id: int):
    latest = get_latest_version(bank_id)
    if latest is None:
        raise BankAccessError("Latest version not found.")
    purchases = get_user_purchases_for_bank(user_id, bank_id)
    if purchases and purchases[0].bank_version_id == latest.id:
        raise BankAccessError("User already owns the latest version.")
    price = calculate_upgrade_price(user_id, bank_id)
    try:
        purchase = create_purchase(user_id=user_id, version_id=latest.id, price_paid=price)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return purchase, latest
