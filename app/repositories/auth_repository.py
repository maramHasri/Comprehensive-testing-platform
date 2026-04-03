from app.extensions import db
from app.models import UserSession


def create_session(user_id: int, jti: str, expires_at):
    session = UserSession(user_id=user_id, jti=jti, expires_at=expires_at)
    db.session.add(session)
    db.session.commit()
    return session


def delete_session_by_jti(jti: str):
    UserSession.query.filter_by(jti=jti).delete()
    db.session.commit()