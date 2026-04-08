from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.config import Config

TOKEN_SALT = "email-verify-v1"


class EmailVerificationTokenError(Exception):
    pass


class EmailVerificationTokenExpired(EmailVerificationTokenError):
    pass


class EmailVerificationTokenInvalid(EmailVerificationTokenError):
    pass


def _get_serializer() -> URLSafeTimedSerializer:
    secret = Config.JWT_SECRET_KEY or Config.SECRET_KEY
    if not secret:
        raise EmailVerificationTokenInvalid("Missing token secret key.")
    return URLSafeTimedSerializer(secret_key=secret)


def generate_email_verification_token(user_id: int) -> str:
    serializer = _get_serializer()
    return serializer.dumps({"user_id": int(user_id)}, salt=TOKEN_SALT)


def decode_email_verification_token(token: str, max_age_seconds: int) -> int:
    serializer = _get_serializer()
    try:
        payload = serializer.loads(token, salt=TOKEN_SALT, max_age=max_age_seconds)
    except SignatureExpired as e:
        raise EmailVerificationTokenExpired(str(e))
    except BadSignature as e:
        raise EmailVerificationTokenInvalid(str(e))
    user_id = payload.get("user_id")
    if user_id is None:
        raise EmailVerificationTokenInvalid("Token payload missing user_id.")
    try:
        return int(user_id)
    except (TypeError, ValueError):
        raise EmailVerificationTokenInvalid("Invalid user_id in token.")
