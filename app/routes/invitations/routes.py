from datetime import datetime, date, timedelta
import uuid
from urllib.parse import quote, urlparse

from flask import current_app
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource, reqparse

from app.extensions import db
from app.models import (
    Institution,
    Invitation,
    Membership,
    Organization,
    Provider,
    ProviderStudent,
    ProviderUser,
    Role,
    StudentProfile,
    User,
)
from app.models.membership import MembershipRole, MembershipStatus
from app.models.organization import OrganizationKind
from app.utils.iam_helpers import (
    ensure_institution_organization,
    ensure_membership,
    ensure_independent_teacher_organization,
    get_or_create_platform_organization,
    user_has_any_role,
)
from app.services.email_template_service import send_activation_email
from app.utils.email_verification_token import generate_email_verification_token

invitations_ns = Namespace("Invitations", description="Unified invitation APIs for institutions and providers.")

create_invitation_parser = reqparse.RequestParser()
create_invitation_parser.add_argument("max_uses", type=int, required=False, default=50, location=("json", "form"))
create_invitation_parser.add_argument("expires_in_hours", type=int, required=False, default=72, location=("json", "form"))

register_student_parser = reqparse.RequestParser()
register_student_parser.add_argument("token", type=str, required=False, location=("args", "json", "form"))
register_student_parser.add_argument("invite_link", type=str, required=False, location=("args", "json", "form"))
register_student_parser.add_argument("email", type=str, required=True, location=("args", "json", "form"))
register_student_parser.add_argument("password", type=str, required=True, location=("args", "json", "form"))
register_student_parser.add_argument("full_name", type=str, required=False, location=("args", "json", "form"))
register_student_parser.add_argument("birth_date", type=str, required=False, location=("args", "json", "form"))
register_student_parser.add_argument("phone", type=str, required=False, location=("args", "json", "form"))
register_student_parser.add_argument("country", type=str, required=False, location=("args", "json", "form"))

accept_invitation_parser = reqparse.RequestParser()
accept_invitation_parser.add_argument("token", type=str, required=True, location=("json", "form"))


def _build_invite_link(token: str) -> str:
    base_url = (current_app.config.get("APP_BASE_URL") or "http://localhost:5000").rstrip("/")
    return f"{base_url}/invite/{token}"


def _build_activation_url(token: str) -> str:
    base_url = (current_app.config.get("APP_BASE_URL") or "http://localhost:5000").rstrip("/")
    return f"{base_url}/auth/verify/{quote(token, safe='-_.')}"


def _extract_token_from_invite_link(invite_link: str | None) -> str | None:
    if invite_link is None:
        return None
    raw_link = invite_link.strip()
    if not raw_link:
        return None
    parsed = urlparse(raw_link)
    path = (parsed.path or "").strip("/")
    if not path:
        return None
    parts = path.split("/")
    if len(parts) >= 2 and parts[-2] == "invite":
        return parts[-1]
    return None


def _is_invitation_valid(invitation: Invitation) -> bool:
    if invitation.expires_at <= datetime.utcnow():
        return False
    if invitation.used_count >= invitation.max_uses:
        return False
    return True


def _resolve_sender_name(invitation: Invitation) -> str | None:
    if invitation.sender_type == "institution":
        institution = Institution.query.filter_by(id=invitation.sender_id).first()
        return institution.name if institution else None
    provider_owner = User.query.get(invitation.sender_id)
    if provider_owner is None:
        return None
    membership = ProviderUser.query.filter_by(user_id=provider_owner.id).first()
    if membership is None:
        return provider_owner.full_name
    provider = Provider.query.get(membership.provider_id)
    if provider is None:
        return provider_owner.full_name
    return provider.full_name or provider_owner.full_name


def _get_sender_from_identity(identity: str | int | None) -> tuple[str | None, int | None, str | None]:
    if identity is None:
        return None, None, None
    identity_str = str(identity)
    institution = Institution.query.get(identity_str.lower())
    if institution is not None:
        if institution.trust_level not in ("trust", "trusted", "verified"):
            return None, None, None
        return "institution", int(institution.id), institution.name
    if not identity_str.isdigit():
        return None, None, None
    user_id = int(identity_str)
    staff_membership_roles = {
        MembershipRole.TEACHER.value,
        MembershipRole.ADMIN.value,
        MembershipRole.EXAMINER.value,
    }
    for m in (
        Membership.query.filter_by(user_id=user_id, status=MembershipStatus.ACTIVE.value)
        .join(Organization, Membership.organization_id == Organization.id)
        .all()
    ):
        if m.role not in staff_membership_roles:
            continue
        org = m.organization
        if org is None:
            continue
        if org.kind == OrganizationKind.INSTITUTION.value and org.institution_id is not None:
            institution_by_membership = Institution.query.filter_by(id=org.institution_id).first()
            if (
                institution_by_membership is not None
                and institution_by_membership.trust_level in ("trust", "trusted", "verified")
            ):
                return "institution", int(institution_by_membership.id), institution_by_membership.name
        if org.kind == OrganizationKind.PROVIDER.value and org.provider_id is not None:
            provider = Provider.query.get(org.provider_id)
            provider_user = User.query.get(user_id)
            if provider is not None and provider.trust_level in ("trust", "trusted", "verified"):
                sender_name = provider.full_name or (provider_user.full_name if provider_user else None)
                return "provider", user_id, sender_name
    provider_membership = ProviderUser.query.filter_by(user_id=user_id).first()
    provider = None
    if provider_membership is not None:
        provider = Provider.query.get(provider_membership.provider_id)
    if provider is None:
        provider_user = User.query.get(user_id)
        if provider_user is not None:
            provider = Provider.query.filter_by(email=provider_user.email).first()
    if provider is None or provider.trust_level not in ("trust", "trusted", "verified"):
        return None, None, None
    provider_user = User.query.get(user_id)
    sender_name = provider.full_name if provider and provider.full_name else (provider_user.full_name if provider_user else None)
    return "provider", user_id, sender_name


def _link_student_with_sender(invitation: Invitation, user: User) -> bool:
    if invitation.sender_type == "institution":
        institution = Institution.query.filter_by(id=invitation.sender_id).first()
        if institution is None:
            return False
        org_id = ensure_institution_organization(institution)
        existing_m = Membership.query.filter_by(user_id=user.id, organization_id=org_id).first()
        if existing_m is not None:
            return False
        ensure_membership(user.id, org_id, MembershipRole.STUDENT.value, status=MembershipStatus.ACTIVE.value)
        return True
    provider_owner_id = invitation.sender_id
    provider_membership = ProviderUser.query.filter_by(user_id=provider_owner_id).first()
    provider_id = provider_membership.provider_id if provider_membership is not None else None
    if provider_id is None:
        provider_owner = User.query.get(provider_owner_id)
        if provider_owner is not None:
            legacy_provider = Provider.query.filter_by(email=provider_owner.email).first()
            if legacy_provider is not None:
                provider_id = legacy_provider.id
                db.session.add(
                    ProviderUser(
                        user_id=provider_owner_id,
                        provider_id=provider_id,
                        role="admin",
                    )
                )
                db.session.flush()
    if provider_id is None:
        raise ValueError("Provider sender is invalid.")
    provider = Provider.query.get(provider_id)
    if provider is None:
        raise ValueError("Provider sender is invalid.")
    org_id = ensure_independent_teacher_organization(provider)
    existing_m = Membership.query.filter_by(user_id=user.id, organization_id=org_id).first()
    if existing_m is not None:
        return False
    ensure_membership(user.id, org_id, MembershipRole.STUDENT.value, status=MembershipStatus.ACTIVE.value)
    existing_provider_student = ProviderStudent.query.filter_by(
        provider_id=provider_id,
        user_id=user.id,
    ).first()
    if existing_provider_student is not None:
        return False
    db.session.add(
        ProviderStudent(
            provider_id=provider_id,
            user_id=user.id,
        )
    )
    return True


@invitations_ns.route("/invitations")
class Invitations(Resource):
    @jwt_required()
    @invitations_ns.expect(create_invitation_parser)
    def post(self):
        args = create_invitation_parser.parse_args()
        max_uses = int(args.get("max_uses") or 50)
        expires_in_hours = int(args.get("expires_in_hours") or 72)
        if max_uses <= 0:
            return {"message": "max_uses must be greater than 0."}, 400
        if expires_in_hours <= 0:
            return {"message": "expires_in_hours must be greater than 0."}, 400
        sender_type, sender_id, _ = _get_sender_from_identity(get_jwt_identity())
        if sender_type is None or sender_id is None:
            return {"message": "Forbidden. Only trusted institution or provider accounts can create invitations."}, 403
        invitation = Invitation(
            token=str(uuid.uuid4()),
            sender_type=sender_type,
            sender_id=sender_id,
            role="student",
            max_uses=max_uses,
            used_count=0,
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours),
        )
        db.session.add(invitation)
        db.session.commit()
        return {
            "invite_link": _build_invite_link(invitation.token),
            "expires_at": invitation.expires_at.isoformat(),
            "max_uses": invitation.max_uses,
        }, 201


@invitations_ns.route("/invitations/<string:token>")
class ValidateInvitation(Resource):
    def get(self, token: str):
        invitation = Invitation.query.filter_by(token=token).first()
        if invitation is None or not _is_invitation_valid(invitation):
            return {
                "valid": False,
                "error": "Invalid or expired invitation",
            }, 200
        remaining_uses = invitation.max_uses - invitation.used_count
        return {
            "valid": True,
            "sender_type": invitation.sender_type,
            "sender_id": invitation.sender_id,
            "remaining_uses": remaining_uses,
        }, 200


@invitations_ns.route("/auth/register-student")
class RegisterStudentByInvitation(Resource):
    @invitations_ns.expect(register_student_parser)
    def post(self):
        args = register_student_parser.parse_args()
        token = (args.get("token") or "").strip()
        if not token:
            token = (_extract_token_from_invite_link(args.get("invite_link")) or "").strip()
        if not token:
            return {"message": "token is required (raw token or invite_link)."}, 400
        email = (args.get("email") or "").strip().lower()
        password = args.get("password") or ""
        full_name = (args.get("full_name") or "").strip()
        birth_date_raw = (args.get("birth_date") or "").strip()
        phone = (args.get("phone") or "").strip() or None
        country = (args.get("country") or "").strip() or None
        birth_date_value: date | None = None
        if birth_date_raw:
            try:
                birth_date_value = datetime.strptime(birth_date_raw, "%Y-%m-%d").date()
            except ValueError:
                return {"message": "birth_date must be in YYYY-MM-DD format."}, 400
        invitation = Invitation.query.filter_by(token=token).first()
        if invitation is None:
            return {"message": "Invitation not found."}, 404
        if not _is_invitation_valid(invitation):
            return {"message": "Invitation is expired or no longer usable."}, 400
        if User.query.filter_by(email=email).first() is not None:
            return {"message": "Email is already registered. Use /api/invitations/accept after login."}, 400
        if len(password) < 8:
            return {"message": "Password must be at least 8 characters."}, 400
        if not full_name:
            full_name = email.split("@")[0]
        student = User(
            full_name=full_name,
            email=email,
            phone=phone,
            country=country,
            is_active=False,
        )
        student.set_password(password)
        student_role = Role.query.filter_by(name="student").first()
        if student_role is None:
            student_role = Role(name="student")
            db.session.add(student_role)
            db.session.flush()
        student.roles.append(student_role)
        db.session.add(student)
        db.session.flush()
        db.session.add(
            StudentProfile(
                user_id=student.id,
                full_name=full_name,
                birth_date=birth_date_value,
            )
        )
        platform_org = get_or_create_platform_organization()
        ensure_membership(student.id, platform_org.id, MembershipRole.STUDENT.value, status=MembershipStatus.ACTIVE.value)
        try:
            _link_student_with_sender(invitation, student)
        except ValueError as err:
            db.session.rollback()
            return {"message": str(err)}, 400
        invitation.used_count += 1
        db.session.commit()
        activation_token = generate_email_verification_token(student.id)
        send_activation_email(student.email, _build_activation_url(activation_token))
        return {
            "message": "Student registered and linked successfully. Verify email before login.",
            "user_id": student.id,
        }, 201


@invitations_ns.route("/invitations/accept")
class AcceptInvitation(Resource):
    @jwt_required()
    @invitations_ns.expect(accept_invitation_parser)
    def post(self):
        args = accept_invitation_parser.parse_args()
        token = (args.get("token") or "").strip()
        invitation = Invitation.query.filter_by(token=token).first()
        if invitation is None:
            return {"message": "Invitation not found."}, 404
        if not _is_invitation_valid(invitation):
            return {"message": "Invitation is expired or no longer usable."}, 400
        identity = str(get_jwt_identity() or "")
        if not identity.isdigit():
            return {"message": "Only user accounts can accept invitation links."}, 403
        user = User.query.get(int(identity))
        if user is None:
            return {"message": "User not found."}, 404
        if not user_has_any_role(user, "student"):
            return {"message": "Only student accounts can accept invitation links."}, 403
        try:
            is_linked = _link_student_with_sender(invitation, user)
        except ValueError as err:
            return {"message": str(err)}, 400
        if not is_linked:
            return {"message": "Student is already linked to this sender."}, 200
        invitation.used_count += 1
        db.session.commit()
        return {"message": "Invitation accepted and student linked successfully."}, 200

