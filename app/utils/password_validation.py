"""
Password strength validation for reset and registration.
Returns message keys (e.g. AUTH_PASSWORD_TOO_SHORT) for localization.
"""
import re


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate new password: min 8 chars, letters and numbers.
    Returns (True, "") if valid, (False, "message_key") otherwise for i18n.
    """
    if len(password) < 8:
        return False, "AUTH_PASSWORD_TOO_SHORT"
    if not re.search(r"[a-zA-Z]", password):
        return False, "AUTH_PASSWORD_NEEDS_LETTER"
    if not re.search(r"\d", password):
        return False, "AUTH_PASSWORD_NEEDS_NUMBER"
    return True, ""
