"""
Stores hashed OTP for password reset. OTP is never stored in plain text.
Single-use: after verify_otp we set verified_at; after reset_password we delete the token.
"""
from datetime import datetime, timedelta

from app.extensions import db


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    otp_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    verified_at = db.Column(db.DateTime, nullable=True)  # Set when OTP is successfully verified
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("password_reset_tokens", lazy="dynamic", cascade="all, delete-orphan"))

    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    def is_verified(self):
        return self.verified_at is not None

    def is_valid_for_reset(self, verified_window_minutes):
        """True if token was verified and still within the allowed window to set new password."""
        if not self.verified_at:
            return False
        return datetime.utcnow() <= self.verified_at + timedelta(minutes=verified_window_minutes)
