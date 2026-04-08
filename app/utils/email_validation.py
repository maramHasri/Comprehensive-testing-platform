import re

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def is_valid_email(email: str) -> bool:
    if not isinstance(email, str):
        return False
    candidate = email.strip()
    if not candidate:
        return False
    return EMAIL_REGEX.match(candidate) is not None
