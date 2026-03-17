"""
Helpers for request input: trim strings, validate length.
Used so backend never relies on client JSON escaping; form inputs are normalized.
"""

MIN_TITLE_LENGTH = 1
MIN_QUESTION_TEXT_LENGTH = 1
MIN_ANSWER_TEXT_LENGTH = 1
MAX_QUESTION_TEXT_LENGTH = 50_000
MAX_ANSWER_TEXT_LENGTH = 2_000


def trim_str(value, default=""):
    """Return trimmed string; if None or not string, return default."""
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    return str(value).strip() if value != "" else default


def validate_required_str(value, field_name, min_len=1, max_len=None):
    """
    Validate required string: trim and check length.
    Returns (trimmed_value, None) if valid, (None, error_message) otherwise.
    """
    s = trim_str(value, "")
    if not s:
        return None, f"{field_name} is required."
    if len(s) < min_len:
        return None, f"{field_name} must be at least {min_len} character(s)."
    if max_len is not None and len(s) > max_len:
        return None, f"{field_name} must be at most {max_len} characters."
    return s, None


def parse_form_bool(value):
    """Convert form value to bool. Accepts True/False, 'true'/'false', 1/0, 'on'."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return bool(value)
