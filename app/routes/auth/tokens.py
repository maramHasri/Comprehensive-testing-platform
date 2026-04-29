"""
Signed, time-limited email verification tokens (itsdangerous URLSafeTimedSerializer).

Used by registration and resend flows. Payload contains only ``user_id`` (no PII in plaintext).
Prefer importing from here in auth code so token rules stay in one place for future reuse
(e.g. password-reset links with a different salt).
"""
from flask import current_app, has_request_context

from app.utils.email_verification_token import (
    decode_email_verification_token,
    generate_email_verification_token,
    EmailVerificationTokenExpired,
    EmailVerificationTokenInvalid,
)


def generate_verification_token(user_id: int) -> str:
    """Return a URL-safe signed token bound to ``user_id`` (no expiry until verified server-side)."""
    return generate_email_verification_token(int(user_id))


def verify_verification_token(token: str) -> int:
    """
    Decode and validate ``token``; return ``user_id`` if valid and not expired.

    Expiry is read from ``EMAIL_VERIFY_TOKEN_EXPIRY_SECONDS`` when a Flask app context exists;
    otherwise the default matches ``Config`` (30 minutes).
    """
    cleaned = (token or "").strip()
    if not cleaned:
        raise EmailVerificationTokenInvalid("Empty verification token.")
    max_age_seconds = 30 * 60
    if has_request_context():
        max_age_seconds = int(
            current_app.config.get("EMAIL_VERIFY_TOKEN_EXPIRY_SECONDS", max_age_seconds)
        )
    return decode_email_verification_token(cleaned, max_age_seconds=max_age_seconds)
