from app.extensions import db
from app.models import BankTopic, BankVersion


def get_latest_version(bank_id: int):
    return (
        BankVersion.query.filter_by(bank_id=bank_id)
        .order_by(BankVersion.version_number.desc(), BankVersion.id.desc())
        .first()
    )


def get_version_by_id(version_id: int):
    return BankVersion.query.get(version_id)


def create_version(bank_id: int, version_number: int, price: float, update_type: str):
    version = BankVersion(
        bank_id=bank_id,
        version_number=version_number,
        price=price,
        update_type=update_type,
    )
    db.session.add(version)
    db.session.flush()
    return version


def get_versions_by_bank(bank_id: int):
    return (
        BankVersion.query.filter_by(bank_id=bank_id)
        .order_by(BankVersion.version_number.asc(), BankVersion.id.asc())
        .all()
    )


def sync_topic_counts_for_bank(bank_id: int) -> int:
    """Set topic_count on all versions of this bank to the number of BankTopic rows."""
    count = BankTopic.query.filter_by(bank_id=bank_id).count()
    BankVersion.query.filter_by(bank_id=bank_id).update(
        {BankVersion.topic_count: count},
        synchronize_session=False,
    )
    return count
