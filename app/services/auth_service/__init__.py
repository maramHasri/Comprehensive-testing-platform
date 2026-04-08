"""Auth business logic: register, verify email, login, logout."""
import logging
import uuid
from datetime import datetime, timedelta

from flask import current_app
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.repositories.auth_repository import create_session, delete_session_by_jti
from app.repositories.user_repository import create_user, get_user_by_email, get_user_by_id
from app.repositories.message_repository import get_message
from app.services.email_template_service import send_activation_email
from app.utils.email_verification_token import (
    decode_email_verification_token,
    generate_email_verification_token,
    EmailVerificationTokenExpired,
    EmailVerificationTokenInvalid,
)
from app.utils.localization import get_current_lang
from app.utils.email_validation import is_valid_email

_auth_log = logging.getLogger(__name__)


def _build_activation_url(token: str) -> str:
    base = (current_app.config.get("APP_BASE_URL") or "").rstrip("/")
    return f"{base}/auth/verify-email?token={token}"


def _send_activation_for_user(user) -> bool:
    token = generate_email_verification_token(user.id)
    activation_url = _build_activation_url(token)
    return send_activation_email(user.email, activation_url)


def register(name: str, email: str, password: str, role: str, lang: str | None = None) -> tuple[dict, int]:
    if lang is None:
        lang = get_current_lang()
    if not (name or "").strip():
        return {"message": get_message("AUTH_NAME_REQUIRED", lang)}, 400
    if not (email or "").strip():
        return {"message": get_message("AUTH_EMAIL_REQUIRED", lang)}, 400
    if not is_valid_email(email):
        return {"message": get_message("AUTH_EMAIL_INVALID", lang)}, 400
    if len(password or "") < 8:
        return {"message": get_message("AUTH_PASSWORD_TOO_SHORT", lang)}, 400
    if (role or "").strip().lower() not in ("teacher", "student", "admin"):
        return {"message": get_message("AUTH_ROLE_INVALID", lang)}, 400
    if get_user_by_email(email.strip()):
        return {"message": get_message("AUTH_EMAIL_EXISTS", lang)}, 400

    user = create_user(name.strip(), email.strip(), password, role.strip().lower())
    user.is_verified = False
    db.session.commit()

    if not _send_activation_for_user(user):
        _auth_log.warning("[auth] registration created user_id=%s but activation email failed", user.id)
        return {"message": get_message("AUTH_EMAIL_SEND_FAILED", lang)}, 503

    return {"message": get_message("AUTH_REGISTER_VERIFY_SENT", lang)}, 201


def verify_email_token(token: str, lang: str | None = None) -> tuple[dict, int]:
    if lang is None:
        lang = get_current_lang()
    if not (token or "").strip():
        return {"message": get_message("AUTH_VERIFY_TOKEN_REQUIRED", lang)}, 400

    max_age = int(current_app.config.get("EMAIL_VERIFY_TOKEN_EXPIRY_SECONDS", 1800))
    try:
        user_id = decode_email_verification_token(token.strip(), max_age_seconds=max_age)
    except EmailVerificationTokenExpired:
        return {"message": get_message("AUTH_VERIFY_TOKEN_EXPIRED", lang)}, 400
    except EmailVerificationTokenInvalid:
        return {"message": get_message("AUTH_VERIFY_TOKEN_INVALID", lang)}, 400

    user = get_user_by_id(user_id)
    if not user:
        return {"message": get_message("AUTH_VERIFY_TOKEN_INVALID", lang)}, 400
    if user.is_verified:
        return {"message": get_message("AUTH_EMAIL_ALREADY_VERIFIED", lang)}, 200

    user.is_verified = True
    db.session.commit()
    return {"message": get_message("AUTH_EMAIL_VERIFIED", lang)}, 200


def resend_verification(email: str, lang: str | None = None) -> tuple[dict, int]:
    if lang is None:
        lang = get_current_lang()
    if not (email or "").strip():
        return {"message": get_message("AUTH_EMAIL_REQUIRED", lang)}, 400
    if not is_valid_email(email):
        return {"message": get_message("AUTH_EMAIL_INVALID", lang)}, 400

    user = get_user_by_email(email.strip())
    if not user:
        # Avoid enumeration
        return {"message": get_message("AUTH_RESEND_VERIFY_GENERIC", lang)}, 200
    if user.is_verified:
        return {"message": get_message("AUTH_EMAIL_ALREADY_VERIFIED", lang)}, 200

    if not _send_activation_for_user(user):
        return {"message": get_message("AUTH_EMAIL_SEND_FAILED", lang)}, 503
    return {"message": get_message("AUTH_RESEND_VERIFY_GENERIC", lang)}, 200


def login(email: str, password: str, lang: str | None = None) -> tuple[dict, int]:
    if lang is None:
        lang = get_current_lang()
    if not (email or "").strip():
        return {"message": get_message("AUTH_EMAIL_REQUIRED", lang)}, 400
    if not is_valid_email(email):
        return {"message": get_message("AUTH_EMAIL_INVALID", lang)}, 400
    if not (password or ""):
        return {"message": get_message("AUTH_PASSWORD_REQUIRED", lang)}, 400
    user = get_user_by_email(email.strip())
    if not user or not user.check_password(password):
        return {"message": get_message("AUTH_LOGIN_INVALID", lang)}, 401
    if not user.is_verified:
        return {"message": get_message("AUTH_VERIFY_REQUIRED", lang)}, 403

    expires_delta = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES") or timedelta(days=7)
    expires_at = datetime.utcnow() + expires_delta
    jti = str(uuid.uuid4())
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "jti": jti},
        expires_delta=expires_delta,
    )
    create_session(user.id, jti, expires_at)
    return {"token": access_token}, 200


def logout(jti: str, lang: str | None = None) -> tuple[dict, int]:
    if lang is None:
        lang = get_current_lang()
    if jti:
        delete_session_by_jti(jti)
    return {"message": get_message("AUTH_LOGOUT_SUCCESS", lang)}, 200
