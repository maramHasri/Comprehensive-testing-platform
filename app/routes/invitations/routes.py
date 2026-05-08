from datetime import date, datetime, timedelta
import logging

from flask import current_app
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource, reqparse

from app.extensions import db
from app.models import Invitation, Membership, Organization, StudentProfile, User
from app.models.membership import MembershipRole, MembershipStatus
from app.utils.iam_helpers import ensure_membership
from app.utils.invitation_token import (
    InvitationTokenExpired,
    InvitationTokenInvalid,
    decode_invitation_token,
    generate_invitation_token,
)

invitations_ns = Namespace("Invitations", description="CB-RBAC student invitation APIs.")
_invitation_log = logging.getLogger(__name__)

create_invitation_parser = reqparse.RequestParser()
create_invitation_parser.add_argument("organization_id", type=int, required=True, location=("args", "json", "form"))
create_invitation_parser.add_argument("target_email", type=str, required=False, location=("args", "json", "form"))
create_invitation_parser.add_argument("max_uses", type=int, required=False, default=1, location=("args", "json", "form"))
create_invitation_parser.add_argument("expires_in_hours", type=int, required=False, default=72, location=("args", "json", "form"))

redeem_invitation_parser = reqparse.RequestParser()
redeem_invitation_parser.add_argument("token", type=str, required=True, location=("json", "form"))
redeem_invitation_parser.add_argument("email", type=str, required=False, location=("json", "form"))
redeem_invitation_parser.add_argument("password", type=str, required=False, location=("json", "form"))
redeem_invitation_parser.add_argument("full_name", type=str, required=False, location=("json", "form"))
redeem_invitation_parser.add_argument("birth_date", type=str, required=False, location=("json", "form"))
redeem_invitation_parser.add_argument("phone", type=str, required=False, location=("json", "form"))
redeem_invitation_parser.add_argument("country", type=str, required=False, location=("json", "form"))


def _max_invite_token_age_seconds() -> int:
    return int(current_app.config.get("INVITE_TOKEN_MAX_AGE_SECONDS", 7 * 24 * 3600))


def validate_student_invite_token(token: str) -> tuple[Invitation | None, dict | None, str | None]:
    try:
        payload = decode_invitation_token(token, max_age_seconds=_max_invite_token_age_seconds())
    except InvitationTokenExpired:
        return None, None, "Invitation token expired."
    except InvitationTokenInvalid:
        return None, None, "Invitation token invalid."
    invitation = Invitation.query.get(int(payload["invitation_id"]))
    if invitation is None:
        return None, None, "Invitation not found."
    if invitation.token != token:
        return None, None, "Invitation token mismatch."
    if invitation.expires_at <= datetime.utcnow():
        return None, None, "Invitation is expired."
    if invitation.used_count >= invitation.max_uses:
        return None, None, "Invitation usage limit reached."
    if int(payload["organization_id"]) != int(invitation.sender_id):
        return None, None, "Invitation context mismatch."
    if (payload.get("role") or "").strip().lower() != MembershipRole.STUDENT.value:
        return None, None, "Invitation role is invalid."
    return invitation, payload, None


def _is_authorized_inviter(user_id: int, organization_id: int) -> bool:
    membership = Membership.query.filter_by(
        user_id=user_id,
        organization_id=organization_id,
        status=MembershipStatus.ACTIVE.value,
    ).first()
    if membership is None:
        return False
    return membership.role in (MembershipRole.ADMIN.value, MembershipRole.TEACHER.value)


def _create_student_user_from_payload(args: dict) -> tuple[User | None, str | None]:
    email = (args.get("email") or "").strip().lower()
    password = args.get("password") or ""
    if not email:
        return None, "email is required for unauthenticated invite redemption."
    if len(password) < 8:
        return None, "Password must be at least 8 characters."
    existing = User.query.filter_by(email=email).first()
    if existing is not None:
        return None, "Email already registered. Login and redeem invite again."
    full_name = (args.get("full_name") or "").strip() or email.split("@")[0]
    phone = (args.get("phone") or "").strip() or None
    country = (args.get("country") or "").strip() or None
    birth_date_raw = (args.get("birth_date") or "").strip()
    birth_date_value: date | None = None
    if birth_date_raw:
        try:
            birth_date_value = datetime.strptime(birth_date_raw, "%Y-%m-%d").date()
        except ValueError:
            return None, "birth_date must be in YYYY-MM-DD format."
    user = User(full_name=full_name, email=email, phone=phone, country=country, is_active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    db.session.add(StudentProfile(user_id=user.id, full_name=full_name, birth_date=birth_date_value))
    return user, None


def _ensure_student_membership(user: User, organization_id: int) -> bool:
    existing = Membership.query.filter_by(user_id=user.id, organization_id=organization_id).first()
    if existing is not None:
        return False
    ensure_membership(
        user_id=user.id,
        organization_id=organization_id,
        role=MembershipRole.STUDENT.value,
        status=MembershipStatus.ACTIVE.value,
    )
    return True


@invitations_ns.route("/invitations")
class Invitations(Resource):
    @jwt_required()
    @invitations_ns.expect(create_invitation_parser)
    def post(self):
        args = create_invitation_parser.parse_args()
        identity = str(get_jwt_identity() or "")
        if not identity.isdigit():
            return {"message": "User-account token is required."}, 403
        organization_id = int(args.get("organization_id"))
        max_uses = int(args.get("max_uses") or 1)
        expires_in_hours = int(args.get("expires_in_hours") or 72)
        if max_uses <= 0:
            return {"message": "max_uses must be greater than 0."}, 400
        if expires_in_hours <= 0:
            return {"message": "expires_in_hours must be greater than 0."}, 400
        organization = Organization.query.get(organization_id)
        if organization is None:
            return {"message": "Organization not found."}, 404
        if not _is_authorized_inviter(int(identity), organization_id):
            return {"message": "Only organization admin/teacher can create student invites."}, 403
        target_email = (args.get("target_email") or "").strip().lower() or None
        invitation = Invitation(
            sender_type=organization.kind,
            sender_id=organization_id,
            role=MembershipRole.STUDENT.value,
            max_uses=max_uses,
            used_count=0,
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours),
        )
        db.session.add(invitation)
        db.session.flush()
        signed_token = generate_invitation_token(
            invitation_id=invitation.id,
            organization_id=organization_id,
            role=MembershipRole.STUDENT.value,
            target_email=target_email,
        )
        invitation.token = signed_token
        db.session.commit()
        _invitation_log.info(
            "[invite.create] invitation_id=%s organization_id=%s created_by_user_id=%s target_email=%s",
            invitation.id,
            organization_id,
            identity,
            target_email,
        )
        base_url = (current_app.config.get("APP_BASE_URL") or "http://localhost:5000").rstrip("/")
        invite_link = f"{base_url}/auth/invite/{signed_token}"
        return {
            "invite_link": invite_link,
            "token": signed_token,
            "organization_id": organization_id,
            "role": MembershipRole.STUDENT.value,
            "target_email": target_email,
            "expires_at": invitation.expires_at.isoformat(),
            "max_uses": invitation.max_uses,
        }, 201


@invitations_ns.route("/invitations/redeem")
class RedeemInvitation(Resource):
    @jwt_required(optional=True)
    @invitations_ns.expect(redeem_invitation_parser)
    def post(self):
        args = redeem_invitation_parser.parse_args()
        token = (args.get("token") or "").strip()
        if not token:
            return {"message": "token is required."}, 400
        invitation, payload, error = validate_student_invite_token(token)
        if error:
            return {"message": error}, 400
        target_email = (payload.get("target_email") or "").strip().lower() or None
        identity = get_jwt_identity()
        user: User | None = None
        if identity is not None:
            user_identity = str(identity).strip()
            if not user_identity.isdigit():
                return {"message": "Only user-account tokens can redeem invitations."}, 403
            user = User.query.get(int(user_identity))
            if user is None:
                return {"message": "User not found."}, 404
            if target_email and user.email.strip().lower() != target_email:
                return {"message": "Invitation is bound to another email."}, 403
        else:
            incoming_email = (args.get("email") or "").strip().lower()
            if target_email and incoming_email != target_email:
                return {"message": "Invitation is bound to another email."}, 403
            user, creation_error = _create_student_user_from_payload(args)
            if creation_error:
                return {"message": creation_error}, 400
        membership_created = _ensure_student_membership(user, int(payload["organization_id"]))
        if membership_created:
            invitation.used_count += 1
            _invitation_log.info(
                "[invite.redeem] invitation_id=%s organization_id=%s user_id=%s used_count=%s",
                invitation.id,
                payload["organization_id"],
                user.id,
                invitation.used_count,
            )
        else:
            _invitation_log.info(
                "[invite.redeem.idempotent] invitation_id=%s organization_id=%s user_id=%s",
                invitation.id,
                payload["organization_id"],
                user.id,
            )
        db.session.commit()
        message = (
            "Student onboarding completed via invitation."
            if membership_created
            else "Student already joined this organization."
        )
        return {
            "message": message,
            "user_id": user.id,
            "organization_id": int(payload["organization_id"]),
            "role": MembershipRole.STUDENT.value,
            "membership_created": membership_created,
        }, 200

