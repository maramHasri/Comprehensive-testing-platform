

from urllib.parse import unquote

from app.models.organization import OrganizationKind
from flask import current_app
from flask_restx import Namespace, Resource, inputs, reqparse
from flask_bcrypt import generate_password_hash
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import User, Organization, Membership
from app.models.membership import MembershipRole, MembershipStatus
from app.services.email_template_service import send_activation_email
from app.utils.email_verification_token import generate_email_verification_token
from app.utils.rbac import roles_required

independent_teachers_ns = Namespace(
    "Independent Teachers",
    description="Independent teacher registration and profile management"
)

# =========================================================
# REGISTER PARSER
# =========================================================

teacher_register_parser = reqparse.RequestParser()
teacher_register_parser.add_argument("full_name", type=str, required=True, location=("json"))
teacher_register_parser.add_argument("email", type=str, required=True, location=("json"))
teacher_register_parser.add_argument("password", type=str, required=True, location=("json"))
teacher_register_parser.add_argument("country", type=str, required=False, location=("json"))
teacher_register_parser.add_argument("phone", type=str, required=False, location=("json"))
teacher_register_parser.add_argument("specialization", type=str, required=False, location=("json"))
teacher_register_parser.add_argument("years_of_experience", type=int, required=False, location=("json"))


# =========================================================
# PROFILE UPDATE PARSER
# =========================================================

teacher_profile_parser = reqparse.RequestParser()
teacher_profile_parser.add_argument("full_name", type=str, required=False, location=("json"))
teacher_profile_parser.add_argument("country", type=str, required=False, location=("json"))
teacher_profile_parser.add_argument("phone", type=str, required=False, location=("json"))
teacher_profile_parser.add_argument("specialization", type=str, required=False, location=("json"))
teacher_profile_parser.add_argument("years_of_experience", type=int, required=False, location=("json"))


teacher_admin_approval_parser = reqparse.RequestParser()
teacher_admin_approval_parser.add_argument(
    "admin_approval", type=inputs.boolean, required=True, location=("json", "form"),
)


def get_independent_teacher_organization(user: User) -> Organization | None:
    return (
        Organization.query.join(Membership)
        .filter(
            Membership.user_id == user.id,
            Organization.kind == OrganizationKind.INDEPENDENT_TEACHER.value,
        )
        .first()
    )


def evaluate_teacher_trust_level(teacher_organization: Organization | None) -> str:
    if teacher_organization is None:
        return "BASIC"
    if teacher_organization.kind != OrganizationKind.INDEPENDENT_TEACHER.value:
        return "BASIC"
    return teacher_organization.trust_level or "BASIC"


def apply_independent_teacher_admin_review(organization: Organization, approved: bool) -> None:
    organization.admin_approval = approved
    organization.trust_level = "TRUSTED" if approved else "BASIC"


# =========================================================
# REGISTER TEACHER RESOURCE
# =========================================================

@independent_teachers_ns.route("/register")
class IndependentTeacherRegister(Resource):

    @independent_teachers_ns.expect(teacher_register_parser)
    def post(self):
        payload = teacher_register_parser.parse_args()
        email = (payload.get("email") or "").strip().lower()

        # 1. Check duplicate user
        if User.query.filter_by(email=email).first():
            return {"message": "Email already exists."}, 400

        # Create User object
        user = User(
            full_name=payload.get("full_name"),
            email=email,
            country=payload.get("country"),
            phone=payload.get("phone"),
            is_active=False
        )

        user.password_hash = generate_password_hash(
            payload.get("password")
        ).decode("utf-8")

        db.session.add(user)
        db.session.flush()  # للحصول على user.id قبل الكوميت النهائي

        # 2. Create Organization (teacher scope)
        organization = Organization(
            name=(user.full_name or "").strip(),
            kind=OrganizationKind.INDEPENDENT_TEACHER.value
        )

        db.session.add(organization)
        db.session.flush()

        # 3. Membership (teacher role)
        membership = Membership(
            user_id=user.id,
            organization_id=organization.id,
            role=MembershipRole.TEACHER.value,
            status=MembershipStatus.ACTIVE.value
        )

        db.session.add(membership)

        db.session.commit()

        # 4. Activation email
        try:
            token = generate_email_verification_token(user.id)
            base_url = current_app.config.get("APP_BASE_URL", "").rstrip("/")
            activation_url = f"{base_url}/auth/verify/{token}"
            send_activation_email(user.email, activation_url)
        except Exception as e:
            # تسجيل الخطأ في حال فشل الإرسال (اختياري)
            print(f"Error sending email: {e}")

        return {
            "user_id": user.id,
            "organization_id": organization.id,
            "membership_id": membership.id,
            "admin_approval": organization.admin_approval,
            "trust_level": organization.trust_level,
            "message": "Independent teacher registered successfully. Please verify email."
        }, 201


# =========================================================
# SUPER ADMIN: TEACHER APPROVAL
# =========================================================


@independent_teachers_ns.route("/<string:teacher_email>/admin-approval")
class IndependentTeacherAdminApproval(Resource):

    @jwt_required()
    @roles_required("super_admin", "super admin")
    @independent_teachers_ns.expect(teacher_admin_approval_parser)
    def put(self, teacher_email: str):
        decoded_email = unquote(teacher_email).strip().lower()
        user = User.query.filter_by(email=decoded_email).first()
        if user is None:
            return {"message": "Teacher not found."}, 404
        organization = get_independent_teacher_organization(user)
        if organization is None:
            return {"message": "Independent teacher organization not found."}, 404
        payload = teacher_admin_approval_parser.parse_args()
        apply_independent_teacher_admin_review(organization, payload.get("admin_approval"))
        db.session.commit()
        return {
            "email": user.email,
            "organization_id": organization.id,
            "admin_approval": organization.admin_approval,
            "trust_level": organization.trust_level,
        }, 200


# =========================================================
# PROFILE MANAGEMENT
# =========================================================

@independent_teachers_ns.route("/<int:user_id>/profile")
class IndependentTeacherProfile(Resource):

    @independent_teachers_ns.expect(teacher_profile_parser)
    def put(self, user_id: int):
        user = User.query.get(user_id)

        if user is None:
            return {"message": "Teacher not found."}, 404

        payload = teacher_profile_parser.parse_args()

        for field, value in payload.items():
            if value is not None:
                setattr(user, field, value)

        teacher_org = get_independent_teacher_organization(user)
        trust_level = evaluate_teacher_trust_level(teacher_org)
        db.session.commit()

        return {
            "user_id": user.id,
            "admin_approval": teacher_org.admin_approval if teacher_org else False,
            "trust_level": trust_level
        }, 200


# =========================================================
# GET TEACHER PROFILE
# =========================================================

@independent_teachers_ns.route("/<int:user_id>")
class IndependentTeacherGet(Resource):

    def get(self, user_id: int):
        user = User.query.get(user_id)

        if user is None:
            return {"message": "Teacher not found."}, 404

        membership = Membership.query.filter_by(user_id=user.id).first()
        organization_id = membership.organization_id if membership else None
        teacher_org = get_independent_teacher_organization(user)
        trust_level = evaluate_teacher_trust_level(teacher_org)

        return {
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "country": user.country,
            "phone": user.phone,
            "organization_id": organization_id,
            "admin_approval": teacher_org.admin_approval if teacher_org else False,
            "trust_level": trust_level
        }, 200