from datetime import datetime

from app.extensions import db


class AccountPasswordResetCode(db.Model):
    __tablename__ = "account_password_reset_codes"

    email = db.Column(db.String(120), primary_key=True)
    otp_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
