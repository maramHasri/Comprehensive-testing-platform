"""
Auth data access: users and sessions. No business logic, only DB operations.
"""
from app.extensions import db
from app.models import User, UserSession


def get_user_by_email(email: str):
    return User.query.filter_by(email=email).first()


def create_user(name: str, email: str, role: str) -> User:
    user = User(name=name, email=email, role=role)
    db.session.add(user)
    db.session.flush()
    return user


def create_session(user_id: int, jti: str, expires_at) -> UserSession:
    session = UserSession(user_id=user_id, jti=jti, expires_at=expires_at)
    db.session.add(session)
    db.session.commit()
    return session


def delete_session_by_jti(jti: str) -> None:
    UserSession.query.filter_by(jti=jti).delete()
    db.session.commit()
