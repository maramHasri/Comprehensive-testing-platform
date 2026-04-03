from app.models import AppMessage

# Used when app_messages has no row yet (DB not seeded).
_FALLBACK_EN = {
    "AUTH_NAME_REQUIRED": "Name is required.",
    "AUTH_EMAIL_REQUIRED": "Email is required.",
    "AUTH_PASSWORD_TOO_SHORT": "Password must be at least 8 characters.",
    "AUTH_ROLE_INVALID": "Role must be teacher, student, or admin.",
    "AUTH_EMAIL_EXISTS": "An account with this email already exists.",
    "AUTH_REGISTER_SUCCESS": "Registration successful.",
    "AUTH_PASSWORD_REQUIRED": "Password is required.",
    "AUTH_LOGIN_INVALID": "Invalid email or password.",
    "AUTH_LOGOUT_SUCCESS": "Logged out successfully.",
    "AUTH_TOO_MANY_REQUESTS": "Too many requests. Try again later.",
    "AUTH_FORGOT_PASSWORD_GENERIC": "If an account exists for this email, you will receive reset instructions shortly.",
    "AUTH_EMAIL_SEND_FAILED": "Could not send the reset email. Configure GMAIL_USER and GMAIL_APP_PASSWORD (Google App Password) on the server.",
    "AUTH_EMAIL_AND_OTP_REQUIRED": "Email and OTP are required.",
    "AUTH_OTP_INVALID": "Invalid or expired code.",
    "AUTH_OTP_VERIFIED": "Code verified. You can set a new password.",
    "AUTH_NEW_PASSWORD_REQUIRED": "New password is required.",
    "AUTH_RESET_SESSION_INVALID": "Reset session expired or invalid. Request a new code.",
    "AUTH_RESET_SUCCESS": "Password updated successfully.",
    "AUTH_PASSWORD_NEEDS_LETTER": "Password must include at least one letter.",
    "AUTH_PASSWORD_NEEDS_NUMBER": "Password must include at least one number.",
}


def get_message_row(message_key: str, language: str):
    lang = (language or "en").strip().lower()
    if len(lang) > 2:
        lang = lang[:2]

    return AppMessage.query.filter_by(
        message_key=message_key,
        language=lang
    ).first()


def get_message_row_fallback(message_key: str):
    return AppMessage.query.filter_by(
        message_key=message_key,
        language="en"
    ).first()


def get_message(message_key: str, language: str) -> str:
    """Return translated text for key, or English fallback, or the key itself."""
    row = get_message_row(message_key, language)
    if row:
        return row.message_text
    lang = (language or "en").strip().lower()
    if len(lang) > 2:
        lang = lang[:2]
    if lang != "en":
        fb = get_message_row_fallback(message_key)
        if fb:
            return fb.message_text
    if message_key in _FALLBACK_EN:
        return _FALLBACK_EN[message_key]
    return message_key


def get_message_format(message_key: str, language: str, **kwargs) -> str:
    text = get_message(message_key, language)
    try:
        return text.format(**kwargs)
    except KeyError:
        return text