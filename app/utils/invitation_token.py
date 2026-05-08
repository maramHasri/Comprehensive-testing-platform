from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.config import Config

TOKEN_SALT = "student-invite-v1"


class InvitationTokenError(Exception):
    pass


class InvitationTokenExpired(InvitationTokenError):
    pass


class InvitationTokenInvalid(InvitationTokenError):
    pass


def _get_serializer() -> URLSafeTimedSerializer:
    secret = Config.JWT_SECRET_KEY or Config.SECRET_KEY
    if not secret:
        raise InvitationTokenInvalid("Missing token secret key.")
    return URLSafeTimedSerializer(secret_key=secret)


def generate_invitation_token(
    invitation_id: int,
    organization_id: int,
    role: str,
    target_email: str | None = None,
) -> str:
    serializer = _get_serializer()
    payload = {
        "invitation_id": int(invitation_id),
        "organization_id": int(organization_id),
        "role": str(role).strip().lower(),
        "target_email": (target_email or "").strip().lower() or None,
    }
    return serializer.dumps(payload, salt=TOKEN_SALT)


def decode_invitation_token(token: str, max_age_seconds: int) -> dict:
    serializer = _get_serializer()
    try:
        payload = serializer.loads(token, salt=TOKEN_SALT, max_age=max_age_seconds)
    except SignatureExpired as exc:
        raise InvitationTokenExpired(str(exc))
    except BadSignature as exc:
        raise InvitationTokenInvalid(str(exc))
    if not isinstance(payload, dict):
        raise InvitationTokenInvalid("Token payload is invalid.")
    invitation_id = payload.get("invitation_id")
    organization_id = payload.get("organization_id")
    role = payload.get("role")
    if invitation_id is None or organization_id is None or not role:
        raise InvitationTokenInvalid("Token payload missing required fields.")
    return payload
