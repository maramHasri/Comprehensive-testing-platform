import sys
from pathlib import Path

from flask_bcrypt import generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.models import Institution


def is_bcrypt_hash(value: str | None) -> bool:
    if not value:
        return False
    return value.startswith("$2a$") or value.startswith("$2b$") or value.startswith("$2y$")


def hash_password(plain_password: str) -> str:
    return generate_password_hash(plain_password).decode("utf-8")


def main() -> None:
    app = create_app()
    with app.app_context():
        rows = Institution.query.all()
        migrated = 0
        skipped = 0
        for institution in rows:
            raw_password = (institution.password or "").strip()
            if not raw_password:
                skipped += 1
                continue
            if is_bcrypt_hash(raw_password):
                skipped += 1
                continue
            institution.password = hash_password(raw_password)
            migrated += 1
        db.session.commit()
        print(
            f"institutions total={len(rows)} migrated={migrated} skipped={skipped}"
        )


if __name__ == "__main__":
    main()
