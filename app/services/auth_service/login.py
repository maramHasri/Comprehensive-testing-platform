import uuid
from datetime import datetime, timedelta

from flask import current_app
from flask_jwt_extended import create_access_token

from app.repositories.auth_repository import create_session
from app.repositories.user_repository import get_user_by_email
from app.services.auth_service.validators import validate_login_input


def login_user(email, password):
    error = validate_login_input(email, password)
    if error:
        return None, error

    user = get_user_by_email(email.strip())
    if not user or not user.check_password(password):
        return None, "AUTH_LOGIN_INVALID"

    expires_delta = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES") or timedelta(days=7)
    expires_at = datetime.utcnow() + expires_delta

    jti = str(uuid.uuid4())

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "jti": jti},
        expires_delta=expires_delta,
    )

    create_session(user.id, jti, expires_at)

    return {"token": access_token}, None
