"""
Stores user sessions (issued JWT tokens) so we can track active logins and revoke them (logout).
Each login creates a row; logout deletes it. Progress (e.g. quiz attempts) is tied to the user via JWT identity.
"""
from datetime import datetime

from app.extensions import db


class UserSession(db.Model):
    __tablename__ = "user_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    jti = db.Column(db.String(36), unique=True, nullable=False, index=True)  # JWT ID from token
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("sessions", lazy="dynamic", cascade="all, delete-orphan"))

    def is_expired(self):
        return datetime.utcnow() > self.expires_at
