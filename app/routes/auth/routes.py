"""
Auth resource layer: HTTP only. Extracts params/headers, calls service, returns response.
No business logic, no DB queries. All user-facing messages come from service (DB-backed i18n).
"""
# TODO: Keep only Blueprint/route registration here after modular refactor.
# TODO: Ensure all input validation rules remain in services/auth_service.py.
from flask import make_response, request
from flask_restx import Namespace, Resource, fields, reqparse
from flask_jwt_extended import jwt_required
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import os
import uuid

from app.extensions import db
from app.models import User, Role
from app.utils.localization import get_current_lang
from app.utils.rbac import roles_required
from app.routes.auth.service import build_email_verification_page
from app.services.auth_service import (
    register_institution as register_institution_svc,
    login_institution as login_institution_svc,
    update_institution_profile as update_institution_profile_svc,
    get_institution_by_id as get_institution_by_id_svc,
    verify_email_token as verify_email_token_svc,
    resend_verification as resend_verification_svc,
)

auth_ns = Namespace(
    "Institution authentication",
    description="Authentication APIs. Responses follow Accept-Language (en/ar).",
)
INSTITUTION_TYPES = (
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

register_parser = reqparse.RequestParser()
register_parser.add_argument("name", type=str, required=True, location=("args", "json", "form"), help="Organization Name (required)")
register_parser.add_argument(
    "type",
    type=str,
    required=True,
    location=("args", "json", "form"),
    choices=INSTITUTION_TYPES,
    help="Organization Type (required)",
)
register_parser.add_argument("country", type=str, required=True, location=("args", "json", "form"), help="Country (required)")
register_parser.add_argument("city", type=str, required=True, location=("args", "json", "form"), help="City (required)")
register_parser.add_argument("email", type=str, required=True, location=("args", "json", "form"), help="Email Address (required)")
register_parser.add_argument("password", type=str, required=True, location=("args", "json", "form"), help="Password, min 8 chars (required)")
register_parser.add_argument("phone", type=str, required=True, location=("args", "json", "form"), help="Phone Number (required)")
register_parser.add_argument("responsible_person_name", type=str, required=True, location=("args", "json", "form"), help="Administrator Name (required)")
register_parser.add_argument("short_description", type=str, required=True, location=("args", "json", "form"), help="Brief Description (required)")
register_parser.add_argument("official_website_domain", type=str, required=False, location=("args", "json", "form"))
register_parser.add_argument("institutional_email", type=str, required=False, location=("args", "json", "form"))
register_parser.add_argument("logo", type=FileStorage, required=False, location="files")
register_parser.add_argument("year_of_establishment", type=int, required=False, location=("args", "json", "form"))
register_parser.add_argument("social_links", type=str, required=False, location=("args", "json", "form"))
register_parser.add_argument("official_document", type=FileStorage, required=False, location="files")

login_parser = reqparse.RequestParser()
login_parser.add_argument("email", type=str, required=True, location=("args", "json", "form"), help="Email (required)")
login_parser.add_argument("password", type=str, required=True, location=("args", "json", "form"), help="Password (required)")
update_institution_parser = reqparse.RequestParser()
update_institution_parser.add_argument("name", type=str, required=False, location=("args", "json", "form"))
update_institution_parser.add_argument("type", type=str, required=False, location=("args", "json", "form"), choices=INSTITUTION_TYPES)
update_institution_parser.add_argument("country", type=str, required=False, location=("args", "json", "form"))
update_institution_parser.add_argument("city", type=str, required=False, location=("args", "json", "form"))
update_institution_parser.add_argument("password", type=str, required=False, location=("args", "json", "form"))
update_institution_parser.add_argument("phone", type=str, required=False, location=("args", "json", "form"))
update_institution_parser.add_argument("responsible_person_name", type=str, required=False, location=("args", "json", "form"))
update_institution_parser.add_argument("short_description", type=str, required=False, location=("args", "json", "form"))
update_institution_parser.add_argument("official_website_domain", type=str, required=False, location=("args", "json", "form"))
update_institution_parser.add_argument("institutional_email", type=str, required=False, location=("args", "json", "form"))
update_institution_parser.add_argument("logo", type=FileStorage, required=False, location="files")
update_institution_parser.add_argument("year_of_establishment", type=int, required=False, location=("args", "json", "form"))
update_institution_parser.add_argument("social_links", type=str, required=False, location=("args", "json", "form"))
update_institution_parser.add_argument("official_document", type=FileStorage, required=False, location="files")
update_institution_parser.add_argument("admin_approval", type=bool, required=False, location=("args", "json", "form"))

resend_parser = reqparse.RequestParser()
resend_parser.add_argument(
    "email",
    type=str,
    required=True,
    location=("args", "json", "form"),
    help="User email (required)",
)
assign_role_parser = reqparse.RequestParser()
assign_role_parser.add_argument("user_id", type=int, required=True, location=("json", "form"))
assign_role_parser.add_argument("role", type=str, required=True, location=("json", "form"))

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


def _save_logo_file(logo_file: FileStorage | None) -> str | None:
    if logo_file is None or not logo_file.filename:
        return None
    upload_directory = os.path.join("uploads", "institution_logos")
    os.makedirs(upload_directory, exist_ok=True)
    safe_name = secure_filename(logo_file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = os.path.join(upload_directory, unique_name)
    logo_file.save(file_path)
    return file_path


def _save_official_document_file(document_file: FileStorage | None) -> str | None:
    if document_file is None or not document_file.filename:
        return None
    upload_directory = os.path.join("uploads", "institution_documents")
    os.makedirs(upload_directory, exist_ok=True)
    safe_name = secure_filename(document_file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = os.path.join(upload_directory, unique_name)
    document_file.save(file_path)
    return file_path


@auth_ns.route("/register")
class Register(Resource):
    @auth_ns.doc(description="Register as Educational Institution")
    @auth_ns.expect(register_parser)
    @auth_ns.response(201, "Educational Institution created")
    @auth_ns.response(400, "Validation error")
    def post(self):
        args = register_parser.parse_args()
        logo_path = _save_logo_file(args.get("logo"))
        official_document_path = _save_official_document_file(args.get("official_document"))
        result, status = register_institution_svc(
            name=args.get("name"),
            type=args.get("type"),
            country=args.get("country"),
            city=args.get("city"),
            email=args.get("email"),
            password=args.get("password"),
            phone=args.get("phone"),
            responsible_person_name=args.get("responsible_person_name"),
            short_description=args.get("short_description"),
            official_website_domain=args.get("official_website_domain"),
            institutional_email=args.get("institutional_email"),
            logo=logo_path,
            year_of_establishment=args.get("year_of_establishment"),
            social_links=args.get("social_links"),
            official_document=official_document_path,
            lang=get_current_lang(),
        )
        return result, status


@auth_ns.route("/login")
class Login(Resource):
    @auth_ns.doc(description="Login as Educational Institution")
    @auth_ns.expect(login_parser)
    @auth_ns.response(401, "Invalid Educational Institution credentials")
    def post(self):
        args = login_parser.parse_args()
        result, status = login_institution_svc(
            email=args.get("email"),
            password=args.get("password"),
            lang=get_current_lang(),
        )
        return result, status


@auth_ns.route("/institutions/<string:institution_email>")
class UpdateInstitution(Resource):
    @auth_ns.doc(description="Update Educational Institution profile (PATCH)")
    @auth_ns.expect(update_institution_parser)
    @auth_ns.response(200, "Educational Institution updated")
    @auth_ns.response(404, "Educational Institution not found")
    def patch(self, institution_email: str):
        args = update_institution_parser.parse_args()
        logo_path = _save_logo_file(args.get("logo"))
        official_document_path = _save_official_document_file(args.get("official_document"))
        result, status = update_institution_profile_svc(
            institution_email=institution_email,
            name=args.get("name"),
            type=args.get("type"),
            country=args.get("country"),
            city=args.get("city"),
            password=args.get("password"),
            phone=args.get("phone"),
            responsible_person_name=args.get("responsible_person_name"),
            short_description=args.get("short_description"),
            official_website_domain=args.get("official_website_domain"),
            institutional_email=args.get("institutional_email"),
            logo=logo_path,
            year_of_establishment=args.get("year_of_establishment"),
            social_links=args.get("social_links"),
            official_document=official_document_path,
            lang=get_current_lang(),
        )
        return result, status


@auth_ns.route("/institutions/id/<int:institution_id>")
class GetInstitutionById(Resource):
    @auth_ns.doc(description="Get Educational Institution by ID")
    @auth_ns.response(200, "Educational Institution data")
    @auth_ns.response(404, "Educational Institution not found")
    def get(self, institution_id: int):
        result, status = get_institution_by_id_svc(institution_id=institution_id)
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

