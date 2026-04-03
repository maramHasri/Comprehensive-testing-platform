from app.extensions import db
from app.models import BankVersion


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
