

from app.models.organization import OrganizationKind
from typing import Any
from flask import request, current_app
from flask_restx import Namespace, Resource, reqparse
from flask_bcrypt import generate_password_hash

from app.extensions import db
from app.models import User, Organization, Membership
from app.models.membership import MembershipRole, MembershipStatus
from app.services.email_template_service import send_activation_email
from app.utils.email_verification_token import generate_email_verification_token

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


# =========================================================
# TRUST LEVEL CALCULATION
# =========================================================

def evaluate_teacher_trust_level(user: User) -> str:
    required_values: list[Any] = [
        user.full_name,
        user.email,
        user.country,
        user.phone,
    ]

    has_basic_fields = all(value not in (None, "") for value in required_values)

    if has_basic_fields:
        return "TRUSTED"

    return "BASIC"


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
            name=f"{user.full_name} - Independent Teacher",
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

        # 4. Trust level
        trust_level = evaluate_teacher_trust_level(user)

        db.session.commit()

        # 5. Activation email
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
            "trust_level": trust_level,
            "message": "Independent teacher registered successfully. Please verify email."
        }, 201


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

        trust_level = evaluate_teacher_trust_level(user)
        db.session.commit()

        return {
            "user_id": user.id,
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
        trust_level = evaluate_teacher_trust_level(user)

        return {
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "country": user.country,
            "phone": user.phone,
            "organization_id": organization_id,
            "trust_level": trust_level
        }, 200