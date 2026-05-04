"""Identity helpers: membership-centric roles and legacy JWT claim mapping."""

from __future__ import annotations

from typing import Any

from app.extensions import db
from app.models.membership import Membership, MembershipRole, MembershipStatus
from app.models.organization import Organization, OrganizationKind


def get_active_memberships_query(user: Any):
    return Membership.query.filter(
        Membership.user_id == user.id,
        Membership.status == MembershipStatus.ACTIVE.value,
    )


def get_or_create_platform_organization() -> Organization:
    org = Organization.query.filter_by(kind=OrganizationKind.PLATFORM.value).first()
    if org is not None:
        return org
    org = Organization(
        kind=OrganizationKind.PLATFORM.value,
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
        kind=OrganizationKind.INSTITUTION.value,
        name=institution.name,
        institution_id=institution.id,
    )
    db.session.add(org)
    db.session.flush()
    return org.id


def ensure_provider_organization(provider: Any) -> int:
    existing = Organization.query.filter_by(provider_id=provider.id).first()
    if existing is not None:
        return existing.id
    display_name = (provider.full_name or provider.email or "").strip() or f"Provider {provider.id}"
    org = Organization(
        kind=OrganizationKind.PROVIDER.value,
        name=display_name,
        provider_id=provider.id,
    )
    db.session.add(org)
    db.session.flush()
    return org.id


def legacy_roles_from_memberships(user: Any) -> set[str]:
    """Map contextual membership roles to legacy token role strings used by existing routes."""
    result: set[str] = set()
    for m in get_active_memberships_query(user).all():
        r = (m.role or "").strip().lower()
        org = Organization.query.get(m.organization_id)
        if org is None:
            continue
        if r == MembershipRole.STUDENT.value:
            result.add("student")
        elif r == MembershipRole.TEACHER.value:
            result.add("instructor")
            if org.kind == OrganizationKind.PROVIDER.value:
                result.add("provider")
                result.add("exam provider")
        elif r == MembershipRole.ADMIN.value:
            result.add("admin")
            if org.kind == OrganizationKind.PLATFORM.value:
                result.add("super_admin")
                result.add("super admin")
            if org.kind == OrganizationKind.INSTITUTION.value:
                result.add("institution")
            if org.kind == OrganizationKind.PROVIDER.value:
                result.add("provider_admin")
                result.add("provider")
                result.add("exam provider")
        elif r == MembershipRole.EXAMINER.value:
            result.add("examiner")
            result.add("instructor")
            if org.kind == OrganizationKind.PROVIDER.value:
                result.add("provider")
                result.add("exam provider")
    return result


def append_global_roles_from_user_roles(user: Any, bucket: set[str]) -> None:
    for role in user.roles:
        name = (role.name or "").strip().lower()
        if name:
            bucket.add(name)


def infer_primary_legacy_role(user: Any) -> str:
    """Single role string for backward-compatible JWT `role` claim."""
    legacy = legacy_roles_from_memberships(user)
    append_global_roles_from_user_roles(user, legacy)
    priority = (
        "super_admin",
        "super admin",
        "institution",
        "provider_admin",
        "provider",
        "exam provider",
        "instructor",
        "admin",
        "teacher",
        "examiner",
        "student",
    )
    for candidate in priority:
        if candidate in legacy:
            if candidate in {"super admin", "super_admin"}:
                return "super_admin"
            if candidate in {"exam provider", "provider", "instructor"} and "provider" in legacy:
                return "provider"
            return candidate
    if legacy:
        return next(iter(sorted(legacy)))
    return "student"


def build_user_jwt_claims(user: Any) -> dict[str, Any]:
    """Additional JWT claims for user-identity tokens (user id as subject)."""
    legacy_membership_roles = legacy_roles_from_memberships(user)
    append_global_roles_from_user_roles(user, legacy_membership_roles)
    primary = infer_primary_legacy_role(user)
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
        "roles": sorted(legacy_membership_roles),
        "memberships": membership_payload,
    }


def user_has_any_legacy_role(user: Any, *role_names: str) -> bool:
    bucket = legacy_roles_from_memberships(user)
    append_global_roles_from_user_roles(user, bucket)
    wanted = {r.strip().lower() for r in role_names if r}
    return not bucket.isdisjoint(wanted)


def user_is_super_admin(user: Any) -> bool:
    bucket = legacy_roles_from_memberships(user)
    append_global_roles_from_user_roles(user, bucket)
    return not bucket.isdisjoint({"super_admin", "super admin"})
