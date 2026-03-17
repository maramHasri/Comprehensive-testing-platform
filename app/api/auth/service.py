"""
Auth business logic: register, login, logout, password reset.
Uses localized messages from message repository; lang from request or argument.
"""
import uuid
from datetime import datetime, timedelta

from flask import current_app

from app.api.auth.repository import (
    get_user_by_email,
    create_user,
    create_session,
    delete_session_by_jti,
)
from app.repositories.message_repository import get_message, get_message_format
from app.utils.localization import get_current_lang
from app.utils.password_validation import validate_password
from app.services.otp_service import (
    create_reset_token_for_user,
    verify_otp_for_user,
    get_verified_token_for_reset,
    consume_token_and_reset_password,
)
from app.services.email_service import send_otp_email
from app.utils.rate_limit import is_rate_limited
from flask_jwt_extended import create_access_token


def register(name: str, email: str, password: str, role: str, lang: str = None) -> tuple[dict, int]:
    """
    Returns (response_dict, status_code). Uses lang for all user-facing messages.
    """
    if lang is None:
        lang = get_current_lang()
    if not (name or "").strip():
        return {"message": get_message("AUTH_NAME_REQUIRED", lang)}, 400
    if not (email or "").strip():
        return {"message": get_message("AUTH_EMAIL_REQUIRED", lang)}, 400
    if len(password or "") < 8:
        return {"message": get_message("AUTH_PASSWORD_TOO_SHORT", lang)}, 400
    if (role or "").strip().lower() not in ("teacher", "student", "admin"):
        return {"message": get_message("AUTH_ROLE_INVALID", lang)}, 400
    if get_user_by_email(email):
        return {"message": get_message("AUTH_EMAIL_EXISTS", lang)}, 400
    user = create_user(name.strip(), email.strip(), role.strip().lower())
    user.set_password(password)
    from app.extensions import db
    db.session.commit()
    return {"message": get_message("AUTH_REGISTER_SUCCESS", lang)}, 201


def login(email: str, password: str, lang: str = None) -> tuple[dict, int]:
    """Returns (response_dict, status_code). On success dict has 'token' key."""
    if lang is None:
        lang = get_current_lang()
    if not (email or "").strip():
        return {"message": get_message("AUTH_EMAIL_REQUIRED", lang)}, 400
    if not (password or ""):
        return {"message": get_message("AUTH_PASSWORD_REQUIRED", lang)}, 400
    user = get_user_by_email(email.strip())
    if not user or not user.check_password(password):
        return {"message": get_message("AUTH_LOGIN_INVALID", lang)}, 401
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


def logout(jti: str, lang: str = None) -> tuple[dict, int]:
    if lang is None:
        lang = get_current_lang()
    if jti:
        delete_session_by_jti(jti)
    return {"message": get_message("AUTH_LOGOUT_SUCCESS", lang)}, 200


def forgot_password(email: str, lang: str = None) -> tuple[dict, int]:
    if lang is None:
        lang = get_current_lang()
    if not (email or "").strip():
        return {"message": get_message("AUTH_EMAIL_REQUIRED", lang)}, 400
    if is_rate_limited(email, current_app.config.get("RATE_LIMIT_FORGOT_PASSWORD", "7 per hour")):
        return {"message": get_message("AUTH_TOO_MANY_REQUESTS", lang)}, 429
    user = get_user_by_email(email.strip())
    msg = get_message("AUTH_FORGOT_PASSWORD_GENERIC", lang)
    if not user:
        return {"message": msg}, 200
    otp = create_reset_token_for_user(user, current_app.config["OTP_EXPIRY_MINUTES"])
    send_otp_email(user.email, otp)
    return {"message": msg}, 200


def verify_otp(email: str, otp: str, lang: str = None) -> tuple[dict, int]:
    if lang is None:
        lang = get_current_lang()
    if not (email or "").strip() or not (otp or "").strip():
        return {"message": get_message("AUTH_EMAIL_AND_OTP_REQUIRED", lang)}, 400
    user = get_user_by_email(email.strip())
    if not user:
        return {"message": get_message("AUTH_OTP_INVALID", lang)}, 400
    if verify_otp_for_user(user.id, otp):
        return {"message": get_message("AUTH_OTP_VERIFIED", lang), "verified": True}, 200
    return {"message": get_message("AUTH_OTP_INVALID", lang)}, 400


def reset_password(email: str, new_password: str, lang: str = None) -> tuple[dict, int]:
    if lang is None:
        lang = get_current_lang()
    if not (email or "").strip():
        return {"message": get_message("AUTH_EMAIL_REQUIRED", lang)}, 400
    if not (new_password or "").strip():
        return {"message": get_message("AUTH_NEW_PASSWORD_REQUIRED", lang)}, 400
    ok, err_key = validate_password(new_password)
    if not ok:
        return {"message": get_message(err_key, lang)}, 400
    user, token = get_verified_token_for_reset(
        email.strip(), current_app.config["OTP_VERIFIED_WINDOW_MINUTES"]
    )
    if not user or not token:
        return {"message": get_message("AUTH_RESET_SESSION_INVALID", lang)}, 400
    consume_token_and_reset_password(user, new_password)
    return {"message": get_message("AUTH_RESET_SUCCESS", lang)}, 200
