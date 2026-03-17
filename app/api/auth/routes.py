"""
Auth resource layer: HTTP only. Extracts params/headers, calls service, returns response.
No business logic, no DB queries. All user-facing messages come from service (DB-backed i18n).
"""
from flask_restx import Namespace, Resource, fields, reqparse
from flask_jwt_extended import jwt_required, get_jwt

from app.utils.localization import get_current_lang
from app.api.auth.service import (
    register as register_svc,
    login as login_svc,
    logout as logout_svc,
    forgot_password as forgot_password_svc,
    verify_otp as verify_otp_svc,
    reset_password as reset_password_svc,
)

auth_ns = Namespace(
    " Authentication",
    description="Register, login, logout, password reset. Responses follow Accept-Language (en/ar).",
)

register_parser = reqparse.RequestParser()
register_parser.add_argument("name", type=str, required=True, location="form", help="Full name (required)")
register_parser.add_argument("email", type=str, required=True, location="form", help="Email (required)")
register_parser.add_argument("password", type=str, required=True, location="form", help="Password, min 8 chars (required)")
register_parser.add_argument("role", type=str, required=True, location="form", choices=("teacher", "student", "admin"), help="teacher | student | admin")

login_parser = reqparse.RequestParser()
login_parser.add_argument("email", type=str, required=True, location="form", help="Email (required)")
login_parser.add_argument("password", type=str, required=True, location="form", help="Password (required)")

forgot_parser = reqparse.RequestParser()
forgot_parser.add_argument("email", type=str, required=True, location="form", help="User email (required)")

verify_otp_parser = reqparse.RequestParser()
verify_otp_parser.add_argument("email", type=str, required=True, location="form", help="Email (required)")
verify_otp_parser.add_argument("otp", type=str, required=True, location="form", help="6-digit OTP (required)")

reset_parser = reqparse.RequestParser()
reset_parser.add_argument("email", type=str, required=True, location="form", help="Email (required)")
reset_parser.add_argument("new_password", type=str, required=True, location="form", help="New password, min 8 chars (required)")

token_model = auth_ns.model("Token", {"token": fields.String})


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
    @auth_ns.marshal_with(token_model)
    @auth_ns.response(401, "Invalid credentials")
    def post(self):
        args = login_parser.parse_args()
        result, status = login_svc(
            email=args.get("email"),
            password=args.get("password"),
            lang=get_current_lang(),
        )
        return result, status


@auth_ns.route("/logout")
class Logout(Resource):
    @auth_ns.response(200, "Logged out")
    @auth_ns.response(401, "Not authenticated")
    @jwt_required()
    def post(self):
        payload = get_jwt()
        jti = payload.get("jti") if payload else None
        result, status = logout_svc(jti=jti, lang=get_current_lang())
        return result, status


@auth_ns.route("/forgot-password")
class ForgotPassword(Resource):
    @auth_ns.expect(forgot_parser)
    @auth_ns.response(200, "Generic message")
    @auth_ns.response(429, "Too many requests")
    def post(self):
        args = forgot_parser.parse_args()
        result, status = forgot_password_svc(email=args.get("email"), lang=get_current_lang())
        return result, status


@auth_ns.route("/verify-otp")
class VerifyOtp(Resource):
    @auth_ns.expect(verify_otp_parser)
    @auth_ns.response(200, "Code verified")
    @auth_ns.response(400, "Invalid or expired code")
    def post(self):
        args = verify_otp_parser.parse_args()
        result, status = verify_otp_svc(
            email=args.get("email"),
            otp=args.get("otp"),
            lang=get_current_lang(),
        )
        return result, status


@auth_ns.route("/reset-password")
class ResetPassword(Resource):
    @auth_ns.expect(reset_parser)
    @auth_ns.response(200, "Password reset successfully")
    @auth_ns.response(400, "Validation error or expired session")
    def post(self):
        args = reset_parser.parse_args()
        result, status = reset_password_svc(
            email=args.get("email"),
            new_password=args.get("new_password"),
            lang=get_current_lang(),
        )
        return result, status
