from functools import wraps

from flask_jwt_extended import get_jwt


def roles_required(*required_roles):
    normalized_required_roles = {role.strip().lower() for role in required_roles if role}

    def decorator(handler):
        @wraps(handler)
        def wrapper(*args, **kwargs):
            claims = get_jwt() or {}
            token_roles = claims.get("roles") or []
            token_role = claims.get("role")
            available_roles = {role.strip().lower() for role in token_roles if isinstance(role, str)}
            if isinstance(token_role, str):
                available_roles.add(token_role.strip().lower())
            if not normalized_required_roles.intersection(available_roles):
                return {"message": "You do not have permission to perform this action."}, 403
            return handler(*args, **kwargs)

        return wrapper

    return decorator
