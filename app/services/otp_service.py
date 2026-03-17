"""
OTP generation, hashing, storage and verification.
OTP is never stored in plain text; only otp_hash and expires_at are persisted.
"""
import secrets
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import func
from app.extensions import db
from app.models import User, PasswordResetToken


def _generate_otp() -> str:
    """Generate a cryptographically secure 6-digit OTP."""
    return "".join(secrets.choice("0123456789") for _ in range(6))


def _hash_otp(otp: str) -> str:
    """Hash OTP for storage (same as password hashing)."""
    return generate_password_hash(otp, method="pbkdf2:sha256")


def _verify_otp_hash(plain_otp: str, otp_hash: str) -> bool:
    return check_password_hash(otp_hash, plain_otp)


def create_reset_token_for_user(user: User, expiry_minutes: int) -> str:
    """
    Create a password reset token for the user: generate OTP, store hash + expiry.
    Returns the plain OTP (only for sending via email; caller must not persist it).
    """
    otp = _generate_otp()
    otp_hash = _hash_otp(otp)
    expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)

    token = PasswordResetToken(
        user_id=user.id,
        otp_hash=otp_hash,
        expires_at=expires_at,
    )
    db.session.add(token)
    db.session.commit()
    return otp


def get_user_by_email(email: str) -> User | None:
    if not email or not email.strip():
        return None
    return User.query.filter(func.lower(User.email) == email.strip().lower()).first()


def get_valid_token_for_verify(user_id: int) -> PasswordResetToken | None:
    """Get the most recent non-expired, not-yet-verified token for the user."""
    return (
        PasswordResetToken.query.filter_by(user_id=user_id, verified_at=None)
        .filter(PasswordResetToken.expires_at > datetime.utcnow())
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )


def verify_otp_for_user(user_id: int, otp: str) -> bool:
    """
    Verify OTP: exists, hash matches, not expired. On success mark token as verified.
    Returns True if valid and marked verified, False otherwise. Single-use.
    """
    token = get_valid_token_for_verify(user_id)
    if not token or not _verify_otp_hash(otp.strip(), token.otp_hash):
        return False
    token.verified_at = datetime.utcnow()
    db.session.commit()
    return True


def get_verified_token_for_reset(email: str, verified_window_minutes: int) -> tuple[User | None, PasswordResetToken | None]:
    """Get user and a token that has been verified and is still within the reset window."""
    user = get_user_by_email(email)
    if not user:
        return None, None
    token = (
        PasswordResetToken.query.filter_by(user_id=user.id)
        .filter(PasswordResetToken.verified_at.isnot(None))
        .order_by(PasswordResetToken.verified_at.desc())
        .first()
    )
    if not token or not token.is_valid_for_reset(verified_window_minutes):
        return user, None
    return user, token


def consume_token_and_reset_password(user: User, new_password: str) -> None:
    """Update user password and delete all reset tokens for this user (single-use, cleanup)."""
    user.set_password(new_password)
    PasswordResetToken.query.filter_by(user_id=user.id).delete()
    db.session.commit()
