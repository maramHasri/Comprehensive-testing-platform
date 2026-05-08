"""Identity helpers based on Membership + Organization only."""

from __future__ import annotations

from typing import Any

from app.extensions import db
from app.models.membership import Membership, MembershipRole, MembershipStatus
from app.models.organization import Organization


def get_active_memberships_query(user: Any):
    return Membership.query.filter(
        Membership.user_id == user.id,
        Membership.status == MembershipStatus.ACTIVE.value,
    )


def get_or_create_platform_organization() -> Organization:
    org = Organization.query.filter_by(kind="platform").first()
    if org is not None:
        return org
    org = Organization(
        kind="platform",
        name="Platform",
    )
    db.session.add(org)
    db.session.flush()
    return org


def ensure_membership(
    user_id: int,
    organization_id: int,
    role: str,
    status: str = MembershipStatus.ACTIVE.value,
) -> Membership:
    existing = Membership.query.filter_by(user_id=user_id, organization_id=organization_id).first()
    if existing is not None:
        return existing
    created = Membership(
        user_id=user_id,
        organization_id=organization_id,
        role=role,
        status=status,
    )
    db.session.add(created)
    return created


def ensure_institution_organization(institution: Any) -> int:
    existing = Organization.query.filter_by(institution_id=institution.id).first()
    if existing is not None:
        return existing.id
    org = Organization(
        kind="institution",
        name=institution.name,
        institution_id=institution.id,
    )
    db.session.add(org)
    db.session.flush()
    return org.id


def ensure_independent_teacher_organization(user: Any) -> int:
    existing = Organization.query.filter_by(kind="independent_teacher", name=user.full_name).first()
    if existing is not None:
        return existing.id
    org = Organization(
        kind="independent_teacher",
        name=user.full_name,
    )
    db.session.add(org)
    db.session.flush()
    return org.id


def get_membership_role_names(user: Any) -> set[str]:
    """Return role names directly from active memberships only."""
    result: set[str] = set()
    for m in get_active_memberships_query(user).all():
        role_name = (m.role or "").strip().lower()
        if role_name:
            result.add(role_name)
    return result


def infer_primary_role(user: Any) -> str:
    """Primary role claim from active memberships."""
    role_names = get_membership_role_names(user)
    if role_names:
        priority = (
            MembershipRole.ADMIN.value,
            MembershipRole.TEACHER.value,
            MembershipRole.INSTITUTION_ADMIN.value,
            MembershipRole.STUDENT.value,
        )
        for candidate in priority:
            if candidate in role_names:
                return candidate
        return next(iter(sorted(role_names)))
    return "student"


def build_user_jwt_claims(user: Any) -> dict[str, Any]:
    """JWT claims derived strictly from memberships."""
    membership_roles = get_membership_role_names(user)
    primary = infer_primary_role(user)
    membership_payload: list[dict[str, Any]] = []
    for m in get_active_memberships_query(user).all():
        org = m.organization
        membership_payload.append(
            {
                "membership_id": m.id,
                "organization_id": m.organization_id,
                "organization_kind": org.kind if org else None,
                "role": m.role,
                "status": m.status,
            }
        )
    return {
        "role": primary,
        "roles": sorted(membership_roles),
        "memberships": membership_payload,
    }


def user_has_any_role(user: Any, *role_names: str) -> bool:
    bucket = get_membership_role_names(user)
    wanted = {r.strip().lower() for r in role_names if r}
    return not bucket.isdisjoint(wanted)


def user_is_super_admin(user: Any) -> bool:
    for membership in get_active_memberships_query(user).all():
        if membership.role != MembershipRole.ADMIN.value:
            continue
        organization = membership.organization
        if organization is not None and organization.kind == "platform":
            return True
    return False

