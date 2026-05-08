from sqlalchemy import func

from app.extensions import db
from app.models import User


def get_user_by_email(email: str):
    """Case-insensitive match so forgot-password/login work across clients and servers."""
    if not email or not str(email).strip():
        return None

    normalized = str(email).strip().lower()

    return User.query.filter(
        func.lower(User.email) == normalized
    ).first()


def get_user_by_id(user_id: int):
    return User.query.get(user_id)


def create_user(name: str, email: str, password: str):
    email_norm = (email or "").strip().lower()
    user_name = (name or "").strip()

    user = User(
        full_name=user_name,
        email=email_norm,
    )

    user.set_password(password)

    db.session.add(user)
    db.session.flush()

    return user