"""Auth business logic: register, verify email, login, logout."""
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from urllib.parse import quote

from flask import current_app
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Institution, User
from app.repositories.auth_repository import create_session, delete_session_by_jti
from app.repositories.user_repository import create_user, get_user_by_email, get_user_by_id, get_role_by_name, create_role
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
INSTITUTION_TYPES: tuple[str, ...] = (
    "university",
    "college",
    "school",
    "training_center",
    "academy",
    "online_platform",
    "company",
    "corporate_training",
    "government",
    "certification_body",
    "testing_center",
    "other",
)


class ActivationLinkOutcome(str, Enum):
    """Result of processing a signed email activation link (no user enumeration for failures)."""

    ACTIVATED = "activated"
    ALREADY_VERIFIED = "already_verified"
    INVALID = "invalid"
    EXPIRED = "expired"
    MISSING_TOKEN = "missing_token"
    USER_MISSING = "user_missing"


def _build_activation_url(token: str) -> str:
    """
    Path-style verify URL (token URL-encoded for safe use in a single path segment).
    Same signing scheme as before; only the delivery URL shape changed.
    """
    base = (current_app.config.get("APP_BASE_URL") or "").rstrip("/")
    encoded = quote(token, safe="-_.")
    return f"{base}/auth/verify/{encoded}"


def _send_activation_for_user(user) -> bool:
    token = generate_email_verification_token(user.id)
    activation_url = _build_activation_url(token)
    return send_activation_email(user.email, activation_url)


def process_activation_link_token(raw_token: str | None) -> ActivationLinkOutcome:
    """
    Validate token, activate account if needed, commit once. Idempotent for already-verified users.

    ``USER_MISSING`` is mapped to the same public messaging as ``INVALID`` at the HTTP/HTML layer
    to avoid leaking whether an id ever existed.
    """
    if not (raw_token or "").strip():
        return ActivationLinkOutcome.MISSING_TOKEN
    token = raw_token.strip()
    max_age = int(current_app.config.get("EMAIL_VERIFY_TOKEN_EXPIRY_SECONDS", 1800))
    try:
        user_id = decode_email_verification_token(token, max_age_seconds=max_age)
    except EmailVerificationTokenExpired:
        return ActivationLinkOutcome.EXPIRED
    except EmailVerificationTokenInvalid:
        return ActivationLinkOutcome.INVALID
    user = get_user_by_id(user_id)
    if not user:
        return ActivationLinkOutcome.USER_MISSING
    if user.is_verified:
        return ActivationLinkOutcome.ALREADY_VERIFIED
    user.is_verified = True
    db.session.commit()
    return ActivationLinkOutcome.ACTIVATED


def _evaluate_institution_trust_level(institution: Institution) -> str:
    has_trusted_fields_count = sum(
        1
        for value in (
            institution.official_website_domain,
            institution.institutional_email,
            institution.logo,
            institution.year_of_establishment,
            institution.social_links,
        )
        if value not in (None, "")
    )
    has_verified_fields = all(
        (
            bool(institution.official_document),
            bool(institution.institutional_email),
            bool(institution.phone),
            bool(institution.admin_approval),
        )
    )
    if has_verified_fields:
        return "verified"
    if has_trusted_fields_count >= 3:
        return "trust"
    return "basic"


def register_institution(
    name: str,
    type: str,
    country: str,
    city: str,
    email: str,
    password: str,
    phone: str,
    responsible_person_name: str,
    short_description: str,
    official_website_domain: str | None = None,
    institutional_email: str | None = None,
    logo: str | None = None,
    year_of_establishment: int | None = None,
    social_links: str | None = None,
    official_document: str | None = None,
    lang: str | None = None,
) -> tuple[dict, int]:
    if lang is None:
        lang = get_current_lang()
    if not (name or "").strip():
        return {"message": get_message("AUTH_NAME_REQUIRED", lang)}, 400
    if not (type or "").strip():
        return {"message": "Organization type is required."}, 400
    if type.strip() not in INSTITUTION_TYPES:
        return {"message": "Organization type is invalid."}, 400
    if not (country or "").strip():
        return {"message": "Country is required."}, 400
    if not (city or "").strip():
        return {"message": "City is required."}, 400
    if not (email or "").strip():
        return {"message": get_message("AUTH_EMAIL_REQUIRED", lang)}, 400
    if not is_valid_email(email):
        return {"message": get_message("AUTH_EMAIL_INVALID", lang)}, 400
    if len(password or "") < 8:
        return {"message": get_message("AUTH_PASSWORD_TOO_SHORT", lang)}, 400
    if not (phone or "").strip():
        return {"message": "Phone number is required."}, 400
    if not (responsible_person_name or "").strip():
        return {"message": "Administrator name is required."}, 400
    if not (short_description or "").strip():
        return {"message": "Brief description is required."}, 400
    if Institution.query.get(email.strip().lower()):
        return {"message": get_message("AUTH_EMAIL_EXISTS", lang)}, 400
    if get_user_by_email(email.strip()):
        return {"message": get_message("AUTH_EMAIL_EXISTS", lang)}, 400
    user = create_user(name.strip(), email.strip(), password, "institution")
    user.phone = phone.strip()
    user.country = country.strip()
    user.is_active = False
    role_name = "institution"
    role_model = get_role_by_name(role_name) or create_role(role_name)
    if role_model not in user.roles:
        user.roles.append(role_model)
    institution = Institution(
        name=name.strip(),
        type=type.strip(),
        country=country.strip(),
        city=city.strip(),
        email=email.strip().lower(),
        password=password,
        phone=phone.strip(),
        responsible_person_name=responsible_person_name.strip(),
        short_description=short_description.strip(),
        official_website_domain=(official_website_domain or "").strip() or None,
        institutional_email=(institutional_email or "").strip() or None,
        logo=(logo or "").strip() or None,
        year_of_establishment=year_of_establishment,
        social_links=(social_links or "").strip() or None,
        official_document=(official_document or "").strip() or None,
        admin_approval=False,
    )
    institution.trust_level = _evaluate_institution_trust_level(institution)
    db.session.add(institution)
    db.session.commit()
    if not _send_activation_for_user(user):
        _auth_log.warning("[auth] institution registration created user_id=%s but activation email failed", user.id)
        return {"message": get_message("AUTH_EMAIL_SEND_FAILED", lang)}, 503
    return {"email": institution.email, "trust_level": institution.trust_level, "message": get_message("AUTH_REGISTER_VERIFY_SENT", lang)}, 201


def verify_email_token(token: str, lang: str | None = None) -> tuple[dict, int]:
    """JSON API: legacy query-token verify and programmatic checks (same rules as link flow)."""
    if lang is None:
        lang = get_current_lang()
    outcome = process_activation_link_token(token)
    if outcome == ActivationLinkOutcome.MISSING_TOKEN:
        return {"message": get_message("AUTH_VERIFY_TOKEN_REQUIRED", lang)}, 400
    if outcome == ActivationLinkOutcome.EXPIRED:
        return {"message": get_message("AUTH_VERIFY_TOKEN_EXPIRED", lang)}, 400
    if outcome in (ActivationLinkOutcome.INVALID, ActivationLinkOutcome.USER_MISSING):
        return {"message": get_message("AUTH_VERIFY_TOKEN_INVALID", lang)}, 400
    if outcome == ActivationLinkOutcome.ALREADY_VERIFIED:
        return {"message": get_message("AUTH_EMAIL_ALREADY_VERIFIED", lang)}, 200
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


def login_institution(email: str, password: str, lang: str | None = None) -> tuple[dict, int]:
    if lang is None:
        lang = get_current_lang()
    if not (email or "").strip():
        return {"message": get_message("AUTH_EMAIL_REQUIRED", lang)}, 400
    if not is_valid_email(email):
        return {"message": get_message("AUTH_EMAIL_INVALID", lang)}, 400
    if not (password or ""):
        return {"message": get_message("AUTH_PASSWORD_REQUIRED", lang)}, 400
    institution = Institution.query.get(email.strip().lower())
    if institution is None or institution.password != password:
        return {"message": get_message("AUTH_LOGIN_INVALID", lang)}, 401
    user = get_user_by_email(email.strip())
    if user is None or not user.is_active:
        return {"message": get_message("AUTH_VERIFY_REQUIRED", lang)}, 403
    expires_delta = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES") or timedelta(days=7)
    access_token = create_access_token(
        identity=institution.email,
        additional_claims={
            "role": "institution",
            "trust_level": institution.trust_level,
        },
        expires_delta=expires_delta,
    )
    return {"token": access_token}, 200


def login_super_admin(email: str, password: str, lang: str | None = None) -> tuple[dict, int]:
    if lang is None:
        lang = get_current_lang()
    if not (email or "").strip():
        return {"message": get_message("AUTH_EMAIL_REQUIRED", lang)}, 400
    if not is_valid_email(email):
        return {"message": get_message("AUTH_EMAIL_INVALID", lang)}, 400
    if not (password or ""):
        return {"message": get_message("AUTH_PASSWORD_REQUIRED", lang)}, 400
    normalized_email = email.strip().lower()
    user = User.query.filter_by(email=normalized_email).first()
    if user is None or not user.check_password(password):
        return {"message": get_message("AUTH_LOGIN_INVALID", lang)}, 401
    role_names = [role.name for role in user.roles]
    if "super_admin" not in role_names and "super admin" not in role_names:
        return {"message": get_message("AUTH_LOGIN_INVALID", lang)}, 401
    expires_delta = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES") or timedelta(days=7)
    expires_at = datetime.utcnow() + expires_delta
    jti = str(uuid.uuid4())
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "role": "super_admin",
            "roles": role_names,
            "jti": jti,
        },
        expires_delta=expires_delta,
    )
    create_session(user.id, jti, expires_at)
    return {"token": access_token}, 200


def update_institution_profile(
    institution_email: str,
    name: str | None = None,
    type: str | None = None,
    country: str | None = None,
    city: str | None = None,
    password: str | None = None,
    phone: str | None = None,
    responsible_person_name: str | None = None,
    short_description: str | None = None,
    official_website_domain: str | None = None,
    institutional_email: str | None = None,
    logo: str | None = None,
    year_of_establishment: int | None = None,
    social_links: str | None = None,
    official_document: str | None = None,
    admin_approval: bool | None = None,
    lang: str | None = None,
) -> tuple[dict, int]:
    if lang is None:
        lang = get_current_lang()
    if not (institution_email or "").strip():
        return {"message": get_message("AUTH_EMAIL_REQUIRED", lang)}, 400
    normalized_email = institution_email.strip().lower()
    institution = Institution.query.get(normalized_email)
    if institution is None:
        return {"message": "Institution not found."}, 404
    if name is not None:
        institution.name = name.strip()
    if type is not None:
        if type.strip() not in INSTITUTION_TYPES:
            return {"message": "Organization type is invalid."}, 400
        institution.type = type.strip()
    if country is not None:
        institution.country = country.strip()
    if city is not None:
        institution.city = city.strip()
    if password is not None:
        institution.password = password
    if phone is not None:
        institution.phone = phone.strip()
    if responsible_person_name is not None:
        institution.responsible_person_name = responsible_person_name.strip()
    if short_description is not None:
        institution.short_description = short_description.strip()
    if official_website_domain is not None:
        institution.official_website_domain = official_website_domain.strip() or None
    if institutional_email is not None:
        institution.institutional_email = institutional_email.strip() or None
    if logo is not None:
        institution.logo = logo.strip() or None
    if year_of_establishment is not None:
        institution.year_of_establishment = year_of_establishment
    if social_links is not None:
        institution.social_links = social_links.strip() or None
    if official_document is not None:
        institution.official_document = official_document.strip() or None
    if admin_approval is not None:
        institution.admin_approval = bool(admin_approval)
    institution.trust_level = _evaluate_institution_trust_level(institution)
    db.session.commit()
    return {"email": institution.email, "trust_level": institution.trust_level}, 200


def get_institution_by_id(institution_id: int) -> tuple[dict, int]:
    institution = Institution.query.filter_by(id=institution_id).first()
    if institution is None:
        return {"message": "Institution not found."}, 404
    return {
        "id": institution.id,
        "email": institution.email,
        "name": institution.name,
        "type": institution.type,
        "country": institution.country,
        "city": institution.city,
        "phone": institution.phone,
        "responsible_person_name": institution.responsible_person_name,
        "short_description": institution.short_description,
        "official_website_domain": institution.official_website_domain,
        "institutional_email": institution.institutional_email,
        "logo": institution.logo,
        "year_of_establishment": institution.year_of_establishment,
        "social_links": institution.social_links,
        "official_document": institution.official_document,
        "admin_approval": institution.admin_approval,
        "trust_level": institution.trust_level,
        "created_at": institution.created_at.isoformat() if institution.created_at else None,
    }, 200


def get_all_institutions() -> tuple[list[dict], int]:
    institutions = Institution.query.order_by(Institution.created_at.desc()).all()
    return [
        {
            "id": institution.id,
            "email": institution.email,
            "name": institution.name,
            "type": institution.type,
            "country": institution.country,
            "city": institution.city,
            "phone": institution.phone,
            "responsible_person_name": institution.responsible_person_name,
            "short_description": institution.short_description,
            "official_website_domain": institution.official_website_domain,
            "institutional_email": institution.institutional_email,
            "logo": institution.logo,
            "year_of_establishment": institution.year_of_establishment,
            "social_links": institution.social_links,
            "official_document": institution.official_document,
            "admin_approval": institution.admin_approval,
            "trust_level": institution.trust_level,
            "created_at": institution.created_at.isoformat() if institution.created_at else None,
        }
        for institution in institutions
    ], 200


def set_institution_admin_approval(institution_id: int, admin_approval: bool) -> tuple[dict, int]:
    institution = Institution.query.filter_by(id=institution_id).first()
    if institution is None:
        return {"message": "Institution not found."}, 404
    institution.admin_approval = bool(admin_approval)
    institution.trust_level = _evaluate_institution_trust_level(institution)
    db.session.commit()
    return {
        "id": institution.id,
        "email": institution.email,
        "admin_approval": institution.admin_approval,
        "trust_level": institution.trust_level,
    }, 200


def get_all_users() -> tuple[list[dict], int]:
    users = User.query.order_by(User.created_at.desc()).all()
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "country": user.country,
            "is_active": user.is_active,
            "roles": [role.name for role in user.roles],
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
        for user in users
    ], 200


def logout(jti: str, lang: str | None = None) -> tuple[dict, int]:
    if lang is None:
        lang = get_current_lang()
    if jti:
        delete_session_by_jti(jti)
    return {"message": get_message("AUTH_LOGOUT_SUCCESS", lang)}, 200
