import os
import uuid
from datetime import datetime, timedelta
from urllib.parse import quote

from flask_bcrypt import check_password_hash, generate_password_hash
from flask import current_app
from flask_jwt_extended import create_access_token
from flask_restx import Namespace, Resource, reqparse
from itsdangerous import URLSafeTimedSerializer
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Provider, ProviderStudent, ProviderUser, Role, User
from app.repositories.auth_repository import create_session
from app.services.email_template_service import send_activation_email
from app.utils.email_verification_token import generate_email_verification_token
from app.utils.iam_helpers import build_user_jwt_claims, ensure_membership, ensure_independent_teacher_organization, user_has_any_role
from app.models.membership import MembershipRole, MembershipStatus

independent_teachers_ns = Namespace(
    "Independent Teachers",
    description="Register and login for independent teachers",
)
# Backward-compatible alias while route modules are being renamed.
exam_providers_ns = independent_teachers_ns

ACCOUNT_TYPES: tuple[str, ...] = ("independent", "institution_linked")

register_exam_provider_parser = reqparse.RequestParser()
register_exam_provider_parser.add_argument("full_name", type=str, required=True, location=("args", "json", "form"))
register_exam_provider_parser.add_argument("email", type=str, required=True, location=("args", "json", "form"))
register_exam_provider_parser.add_argument("password", type=str, required=True, location=("args", "json", "form"))
register_exam_provider_parser.add_argument("country", type=str, required=True, location=("args", "json", "form"))
register_exam_provider_parser.add_argument("specialization", type=str, required=True, location=("args", "json", "form"))
register_exam_provider_parser.add_argument("years_of_experience", type=int, required=True, location=("args", "json", "form"))
register_exam_provider_parser.add_argument("phone", type=str, required=True, location=("args", "json", "form"))
register_exam_provider_parser.add_argument("account_type", type=str, required=True, choices=ACCOUNT_TYPES, location=("args", "json", "form"))
register_exam_provider_parser.add_argument("profile_picture", type=FileStorage, required=False, location="files")
register_exam_provider_parser.add_argument("cv", type=FileStorage, required=False, location="files")
register_exam_provider_parser.add_argument("linkedin_profile", type=str, required=False, location=("args", "json", "form"))
register_exam_provider_parser.add_argument("educational_certificates", type=FileStorage, required=False, location="files")
register_exam_provider_parser.add_argument("current_workplace", type=str, required=False, location=("args", "json", "form"))
register_exam_provider_parser.add_argument("verified_affiliation_with_institution", type=bool, required=False, location=("args", "json", "form"))

login_exam_provider_parser = reqparse.RequestParser()
login_exam_provider_parser.add_argument("email", type=str, required=True, location=("args", "json", "form"))
login_exam_provider_parser.add_argument("password", type=str, required=True, location=("args", "json", "form"))

update_exam_provider_parser = reqparse.RequestParser()
update_exam_provider_parser.add_argument("full_name", type=str, required=False, location=("args", "json", "form"))
update_exam_provider_parser.add_argument("country", type=str, required=False, location=("args", "json", "form"))
update_exam_provider_parser.add_argument("specialization", type=str, required=False, location=("args", "json", "form"))
update_exam_provider_parser.add_argument("years_of_experience", type=int, required=False, location=("args", "json", "form"))
update_exam_provider_parser.add_argument("phone", type=str, required=False, location=("args", "json", "form"))
update_exam_provider_parser.add_argument("account_type", type=str, required=False, choices=ACCOUNT_TYPES, location=("args", "json", "form"))
update_exam_provider_parser.add_argument("profile_picture", type=FileStorage, required=False, location="files")
update_exam_provider_parser.add_argument("cv", type=FileStorage, required=False, location="files")
update_exam_provider_parser.add_argument("linkedin_profile", type=str, required=False, location=("args", "json", "form"))
update_exam_provider_parser.add_argument("educational_certificates", type=FileStorage, required=False, location="files")
update_exam_provider_parser.add_argument("current_workplace", type=str, required=False, location=("args", "json", "form"))
update_exam_provider_parser.add_argument("admin_approval", type=bool, required=False, location=("args", "json", "form"))
update_exam_provider_parser.add_argument("verified_affiliation_with_institution", type=bool, required=False, location=("args", "json", "form"))


def _save_provider_upload(upload_file: FileStorage | None, directory_name: str) -> str | None:
    if upload_file is None or not upload_file.filename:
        return None
    upload_directory = os.path.join("uploads", "exam_providers", directory_name)
    os.makedirs(upload_directory, exist_ok=True)
    safe_name = secure_filename(upload_file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = os.path.join(upload_directory, unique_name)
    upload_file.save(file_path)
    return file_path


def _evaluate_exam_provider_trust_level(provider: Provider) -> str:
    required_values = (
        provider.full_name,
        provider.email,
        provider.password,
        provider.country,
        provider.specialization,
        provider.years_of_experience,
        provider.phone,
        provider.account_type,
    )
    has_basic_level = all(value not in (None, "") for value in required_values)
    optional_values = (
        provider.profile_picture,
        provider.cv,
        provider.linkedin_profile,
        provider.educational_certificates,
        provider.current_workplace,
    )
    optional_count = sum(1 for value in optional_values if value not in (None, ""))
    if bool(provider.admin_approval) and bool(provider.verified_affiliation_with_institution):
        return "verified"
    if has_basic_level and optional_count >= 3:
        return "trust"
    return "basic"


def _get_or_create_provider_role() -> Role:
    provider_role = Role.query.filter_by(name="provider").first()
    if provider_role is None:
        provider_role = Role(name="provider")
        db.session.add(provider_role)
        db.session.flush()
    return provider_role


def _build_student_invitation_link(provider: Provider) -> str:
    serializer = URLSafeTimedSerializer(current_app.config.get("SECRET_KEY", "fallback-secret"))
    token = serializer.dumps({"provider_id": provider.id, "role": "student"})
    base_url = (current_app.config.get("APP_BASE_URL") or "").rstrip("/")
    return f"{base_url}/invite/student?token={quote(token, safe='')}"


def _send_activation_for_user(user: User) -> bool:
    token = generate_email_verification_token(user.id)
    base_url = (current_app.config.get("APP_BASE_URL") or "").rstrip("/")
    encoded_token = quote(token, safe="-_.")
    activation_url = f"{base_url}/auth/verify/{encoded_token}"
    return send_activation_email(user.email, activation_url)


@exam_providers_ns.route("/register")
class RegisterExamProvider(Resource):
    @exam_providers_ns.expect(register_exam_provider_parser)
    def post(self):
        payload = register_exam_provider_parser.parse_args()
        email = (payload.get("email") or "").strip().lower()
        if Provider.query.filter_by(email=email).first() is not None or User.query.filter_by(email=email).first() is not None:
            return {"message": "Email already exists."}, 400
        password_hash = generate_password_hash(payload.get("password") or "").decode("utf-8")
        user = User(
            full_name=(payload.get("full_name") or "").strip(),
            email=email,
            phone=(payload.get("phone") or "").strip() or None,
            country=(payload.get("country") or "").strip() or None,
            is_active=False,
        )
        user.password_hash = password_hash
        db.session.add(user)
        db.session.flush()
        provider_role = _get_or_create_provider_role()
        if provider_role not in user.roles:
            user.roles.append(provider_role)
        provider = Provider(
            type="individual",
            status="active",
            full_name=(payload.get("full_name") or "").strip(),
            email=email,
            password=password_hash,
            country=(payload.get("country") or "").strip(),
            specialization=(payload.get("specialization") or "").strip(),
            years_of_experience=payload.get("years_of_experience"),
            phone=(payload.get("phone") or "").strip(),
            account_type=(payload.get("account_type") or "").strip(),
            profile_picture=_save_provider_upload(payload.get("profile_picture"), "profile_pictures"),
            cv=_save_provider_upload(payload.get("cv"), "cv"),
            linkedin_profile=(payload.get("linkedin_profile") or "").strip() or None,
            educational_certificates=_save_provider_upload(payload.get("educational_certificates"), "educational_certificates"),
            current_workplace=(payload.get("current_workplace") or "").strip() or None,
            admin_approval=False,
            verified_affiliation_with_institution=bool(payload.get("verified_affiliation_with_institution")),
        )
        provider.trust_level = _evaluate_exam_provider_trust_level(provider)
        db.session.add(provider)
        db.session.flush()
        db.session.add(ProviderUser(user_id=user.id, provider_id=provider.id, role="admin"))
        db.session.flush()
        organization_id = ensure_independent_teacher_organization(provider)
        ensure_membership(
            user.id,
            organization_id,
            MembershipRole.ADMIN.value,
            status=MembershipStatus.ACTIVE.value,
        )
        db.session.commit()
        if not _send_activation_for_user(user):
            return {"message": "Registration created, but activation email could not be sent."}, 503
        return {
            "id": provider.id,
            "user_id": user.id,
            "email": provider.email,
            "trust_level": provider.trust_level,
            "message": "Registration successful. Please check your email to activate your account.",
        }, 201


@exam_providers_ns.route("/login")
class LoginExamProvider(Resource):
    @exam_providers_ns.expect(login_exam_provider_parser)
    def post(self):
        payload = login_exam_provider_parser.parse_args()
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        provider = None
        user = User.query.filter_by(email=email).first()
        if user is not None and user.check_password(password):
            if not user.is_active:
                return {"message": "Please verify your email before logging in."}, 403
            has_provider_role = user_has_any_role(user, "provider", "exam provider", "instructor")
            if not has_provider_role:
                return {"message": "Invalid credentials."}, 401
            membership = ProviderUser.query.filter_by(user_id=user.id).first()
            if membership is not None:
                provider = Provider.query.get(membership.provider_id)
            if provider is None:
                provider = Provider.query.filter_by(email=email).first()
        else:
            provider = Provider.query.filter_by(email=email).first()
            if provider is None or not check_password_hash(provider.password or "", password):
                return {"message": "Invalid credentials."}, 401
            membership = ProviderUser.query.filter_by(provider_id=provider.id).first()
            user = User.query.get(membership.user_id) if membership is not None else None
        if provider is None:
            return {"message": "Invalid credentials."}, 401
        expires_delta = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES") or timedelta(days=7)
        expires_at = datetime.utcnow() + expires_delta
        jti = str(uuid.uuid4())
        identity = str(user.id) if user is not None else f"provider:{provider.id}"
        if user is not None:
            claims = build_user_jwt_claims(user)
            claims["jti"] = jti
            claims["role"] = "provider"
            claims["provider_id"] = provider.id
            claims["trust_level"] = provider.trust_level
        else:
            claims = {"role": "provider", "provider_id": provider.id, "trust_level": provider.trust_level, "jti": jti}
        token = create_access_token(
            identity=identity,
            additional_claims=claims,
            expires_delta=expires_delta,
        )
        if user is not None:
            create_session(user.id, jti, expires_at)
        return {"token": token}, 200


@exam_providers_ns.route("/<int:provider_id>")
class UpdateExamProvider(Resource):
    @exam_providers_ns.expect(update_exam_provider_parser)
    def patch(self, provider_id: int):
        provider = Provider.query.get(provider_id)
        if provider is None:
            return {"message": "Exam provider not found."}, 404
        payload = update_exam_provider_parser.parse_args()
        profile_picture_path = _save_provider_upload(payload.get("profile_picture"), "profile_pictures")
        cv_path = _save_provider_upload(payload.get("cv"), "cv")
        educational_certificates_path = _save_provider_upload(payload.get("educational_certificates"), "educational_certificates")
        for field_name in payload:
            field_value = payload.get(field_name)
            if field_value is None:
                continue
            if field_name in {"profile_picture", "cv", "educational_certificates"}:
                continue
            setattr(provider, field_name, field_value)
        if profile_picture_path is not None:
            provider.profile_picture = profile_picture_path
        if cv_path is not None:
            provider.cv = cv_path
        if educational_certificates_path is not None:
            provider.educational_certificates = educational_certificates_path
        provider.trust_level = _evaluate_exam_provider_trust_level(provider)
        db.session.commit()
        return {"id": provider.id, "trust_level": provider.trust_level}, 200


@exam_providers_ns.route("/<int:provider_id>/profile")
class GetExamProviderProfile(Resource):
    def get(self, provider_id: int):
        provider = Provider.query.get(provider_id)
        if provider is None:
            return {"message": "Exam provider not found."}, 404
        invitation_link = None
        if provider.trust_level in {"trust", "verified"}:
            invitation_link = _build_student_invitation_link(provider)
        return {
            "id": provider.id,
            "email": provider.email,
            "full_name": provider.full_name,
            "country": provider.country,
            "specialization": provider.specialization,
            "years_of_experience": provider.years_of_experience,
            "phone": provider.phone,
            "account_type": provider.account_type,
            "profile_picture": provider.profile_picture,
            "cv": provider.cv,
            "linkedin_profile": provider.linkedin_profile,
            "educational_certificates": provider.educational_certificates,
            "current_workplace": provider.current_workplace,
            "admin_approval": provider.admin_approval,
            "verified_affiliation_with_institution": provider.verified_affiliation_with_institution,
            "trust_level": provider.trust_level,
            "student_invitation_link": invitation_link,
        }, 200


@exam_providers_ns.route("/<int:provider_id>/students")
class GetProviderStudents(Resource):
    def get(self, provider_id: int):
        provider = Provider.query.get(provider_id)
        if provider is None:
            return {"message": "Exam provider not found."}, 404
        provider_students = ProviderStudent.query.filter_by(provider_id=provider_id).all()
        students: list[dict] = []
        for provider_student in provider_students:
            student_user = User.query.get(provider_student.user_id)
            if student_user is None:
                continue
            students.append(
                {
                    "id": student_user.id,
                    "full_name": student_user.full_name,
                    "email": student_user.email,
                    "phone": student_user.phone,
                    "country": student_user.country,
                    "is_active": student_user.is_active,
                    "linked_at": provider_student.created_at.isoformat() if provider_student.created_at else None,
                }
            )
        return {
            "provider_id": provider_id,
            "students_count": len(students),
            "students": students,
        }, 200

