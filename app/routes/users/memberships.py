"""Authenticated user memberships (organizational contexts)."""

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource, fields
from sqlalchemy.orm import selectinload

from app.models import Membership, User

users_ns = Namespace(
    "Current user",
    description="Context-based memberships for the authenticated user account.",
)


membership_item_model = users_ns.model(
    "MembershipItem",
    {
        "organization_id": fields.Integer(required=True, description="Organization scope id"),
        "organization_name": fields.String(required=True, description="Display name of the organization"),
        "role": fields.String(
            required=True,
            description="Contextual role in this organization",
            enum=["student", "teacher", "admin", "examiner"],
        ),
        "status": fields.String(
            required=True,
            description="Membership status",
            enum=["active", "suspended"],
        ),
    },
)

memberships_response_model = users_ns.model(
    "UserMembershipsResponse",
    {
        "user_id": fields.Integer(required=True),
        "memberships": fields.List(fields.Nested(membership_item_model), required=True),
    },
)


def _parse_user_id_from_jwt_identity() -> int | None:
    raw = get_jwt_identity()
    if raw is None:
        return None
    s = str(raw).strip()
    if not s.isdigit():
        return None
    return int(s)


@users_ns.route("/me/memberships")
class CurrentUserMemberships(Resource):
    @jwt_required()
    @users_ns.doc(
        "get_current_user_memberships",
        description=(
            "Returns every organizational context (membership) for the authenticated user: "
            "organization id, display name, contextual role, and status. "
            "No global role is implied; roles are per organization."
        ),
        security="Bearer",
    )
    @users_ns.response(200, "OK", memberships_response_model)
    @users_ns.response(401, "Missing or invalid token")
    @users_ns.response(403, "Token is not a user-account subject (e.g. institution session)")
    @users_ns.response(404, "User not found")
    def get(self):
        user_id = _parse_user_id_from_jwt_identity()
        if user_id is None:
            return {"message": "A user-account JWT (numeric subject) is required for this resource."}, 403
        user = User.query.get(user_id)
        if user is None:
            return {"message": "User not found."}, 404
        rows = (
            Membership.query.options(selectinload(Membership.organization))
            .filter(Membership.user_id == user_id)
            .order_by(Membership.organization_id.asc())
            .all()
        )
        memberships_out: list[dict] = []
        for m in rows:
            org = m.organization
            org_name = (org.name if org is not None else "") or ""
            memberships_out.append(
                {
                    "organization_id": m.organization_id,
                    "organization_name": org_name,
                    "role": m.role,
                    "status": m.status,
                }
            )
        return {"user_id": user_id, "memberships": memberships_out}, 200
