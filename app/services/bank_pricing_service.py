from datetime import datetime

from app.models.question_bank import Offer


def can_be_paid(bank_version):
    """
    Paid versions must meet minimum quality constraints.
    """
    return (
        bank_version.question_count >= 100
        and bank_version.topic_count >= 2
    )


def _active_offer(predicate):
    now = datetime.utcnow()
    return (
        Offer.query.filter(predicate)
        .filter(Offer.valid_from <= now, Offer.valid_to >= now)
        .order_by(Offer.discount_percentage.desc())
        .first()
    )


def apply_offer(offer_kind, base_price):
    """
    offer_kind: "first_purchase" | "upgrade"
    """
    if base_price <= 0:
        return 0.0

    if offer_kind == "first_purchase":
        offer = _active_offer(Offer.applies_to_first_purchase.is_(True))
    elif offer_kind == "upgrade":
        offer = _active_offer(Offer.applies_to_upgrade.is_(True))
    else:
        offer = None

    if not offer:
        return float(base_price)

    discounted = float(base_price) * (1 - (float(offer.discount_percentage) / 100.0))
    return round(max(discounted, 0.0), 2)


def calculate_price(user, bank, version):
    """
    Rules-based pricing:
    - first purchase offer if user never purchased this bank
    - upgrade offer if user purchased an older version
    - otherwise base price
    """
    base_price = float(bank.base_price or 0.0)
    if base_price <= 0:
        return 0.0

    if not user.has_purchased(bank):
        return apply_offer("first_purchase", base_price)

    if user.has_old_version(bank, version):
        return apply_offer("upgrade", base_price)

    return base_price
