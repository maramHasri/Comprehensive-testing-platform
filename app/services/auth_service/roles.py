GLOBAL_SYSTEM_ROLES: tuple[str, ...] = (
    "super_admin",
    "student",
    "provider",
)

ALLOWED_REGISTER_ROLES: tuple[str, ...] = GLOBAL_SYSTEM_ROLES
ALLOWED_REGISTER_ROLES_HELP: str = "super_admin | student | provider"


def ensure_default_roles() -> None:
    from app.extensions import db
    from app.models import Role

    for role_name in GLOBAL_SYSTEM_ROLES:
        existing_role = Role.query.filter_by(name=role_name).first()
        if existing_role is None:
            db.session.add(Role(name=role_name))
    db.session.commit()
