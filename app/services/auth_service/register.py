from app.extensions import db
from app.repositories.user_repository import create_user, get_user_by_email
from app.services.auth_service.validators import validate_register_input


def register_user(name, email, password, role):
    error = validate_register_input(name, email, password, role)
    if error:
        return None, error

    if get_user_by_email(email):
        return None, "AUTH_EMAIL_EXISTS"

    user = create_user(name.strip(), email.strip(), password, role.strip().lower())
    db.session.commit()

    return {"message": "AUTH_REGISTER_SUCCESS"}, None
