def validate_register_input(name, email, password, role):
    if not (name or "").strip():
        return "AUTH_NAME_REQUIRED"

    if not (email or "").strip():
        return "AUTH_EMAIL_REQUIRED"

    if len(password or "") < 8:
        return "AUTH_PASSWORD_TOO_SHORT"

    if (role or "").strip().lower() not in ("teacher", "student", "admin"):
        return "AUTH_ROLE_INVALID"

    return None


def validate_login_input(email, password):
    if not (email or "").strip():
        return "AUTH_EMAIL_REQUIRED"

    if not (password or ""):
        return "AUTH_PASSWORD_REQUIRED"

    return None


def validate_reset_password_input(email, new_password):
    if not (email or "").strip():
        return "AUTH_EMAIL_REQUIRED"

    if not (new_password or "").strip():
        return "AUTH_NEW_PASSWORD_REQUIRED"

    return None