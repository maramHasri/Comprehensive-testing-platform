"""
Auth resource layer: HTTP only. Extracts params/headers, calls service, returns response.
No business logic, no DB queries. All user-facing messages come from service (DB-backed i18n).
"""
# TODO: Keep only Blueprint/route registration here after modular refactor.
# TODO: Ensure all input validation rules remain in services/auth_service.py.
from flask import request
from flask_restx import Namespace, Resource, fields, reqparse

from app.utils.localization import get_current_lang
from app.services.auth_service import (
    register as register_svc,
    login as login_svc,
    verify_email_token as verify_email_token_svc,
    resend_verification as resend_verification_svc,
)

auth_ns = Namespace(
    " Authentication",
    description="Register, verify email, login. Responses follow Accept-Language (en/ar).",
)

register_parser = reqparse.RequestParser()
register_parser.add_argument("name", type=str, required=True, location=("args", "json", "form"), help="Full name (required)")
register_parser.add_argument("email", type=str, required=True, location=("args", "json", "form"), help="Email (required)")
register_parser.add_argument("password", type=str, required=True, location=("args", "json", "form"), help="Password, min 8 chars (required)")
register_parser.add_argument("role", type=str, required=True, location=("args", "json", "form"), choices=("teacher", "student", "admin"), help="teacher | student | admin")

login_parser = reqparse.RequestParser()
login_parser.add_argument("email", type=str, required=True, location=("args", "json", "form"), help="Email (required)")
login_parser.add_argument("password", type=str, required=True, location=("args", "json", "form"), help="Password (required)")

resend_parser = reqparse.RequestParser()
resend_parser.add_argument(
    "email",
    type=str,
    required=True,
    location=("args", "json", "form"),
    help="User email (required)",
)

token_model = auth_ns.model("Token", {"token": fields.String})


def _str_or_none(value):
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _email_from_request(parsed_email: str | None) -> str | None:
    body = request.get_json(silent=True) or {}
    raw = (
        request.args.get("email")
        or body.get("email")
        or request.form.get("email")
        or parsed_email
    )
    return _str_or_none(raw)


@auth_ns.route("/register")
class Register(Resource):
    @auth_ns.expect(register_parser)
    @auth_ns.response(201, "User created")
    @auth_ns.response(400, "Validation error")
    def post(self):
        args = register_parser.parse_args()
        result, status = register_svc(
            name=args.get("name"),
            email=args.get("email"),
            password=args.get("password"),
            role=args.get("role"),
            lang=get_current_lang(),
        )
        return result, status


@auth_ns.route("/login")
class Login(Resource):
    @auth_ns.expect(login_parser)
    @auth_ns.response(401, "Invalid credentials")
    def post(self):
        args = login_parser.parse_args()
        result, status = login_svc(
            email=args.get("email"),
            password=args.get("password"),
            lang=get_current_lang(),
        )
        return result, status


@auth_ns.route("/verify-email")
class VerifyEmail(Resource):
    @auth_ns.doc(params={"token": "Verification token sent by email"})
    @auth_ns.response(200, "Email verified")
    @auth_ns.response(400, "Token invalid or expired")
    def get(self):
        token = _str_or_none(request.args.get("token"))
        result, status = verify_email_token_svc(token=token, lang=get_current_lang())
        return result, status


@auth_ns.route("/resend-verification")
class ResendVerification(Resource):
    @auth_ns.expect(resend_parser)
    @auth_ns.response(200, "Generic resend message")
    @auth_ns.response(503, "Email sending failed")
    def post(self):
        parsed = resend_parser.parse_args()
        email = _email_from_request(parsed.get("email"))
        result, status = resend_verification_svc(email=email, lang=get_current_lang())
        return result, status
