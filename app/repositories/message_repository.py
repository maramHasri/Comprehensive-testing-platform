"""
Data access for localized messages. Queries by message_key and language.
Fallback to English if requested language not found.
"""
from app.models import AppMessage


def get_message(message_key: str, language: str) -> str:
    """
    Get localized message from database.
    """
    lang = (language or "en").strip().lower()
    if len(lang) > 2:
        lang = lang[:2]  # e.g. en-US -> en
    row = AppMessage.query.filter_by(message_key=message_key, language=lang).first()
    if row:
        return row.message_text
    if lang != "en":
        row = AppMessage.query.filter_by(message_key=message_key, language="en").first()
        if row:
            return row.message_text
    return message_key


def get_message_format(message_key: str, language: str, **kwargs) -> str:
    """Get localized message and format with kwargs (e.g. {count} -> 5)."""
    text = get_message(message_key, language)
    try:
        return text.format(**kwargs)
    except KeyError:
        return text
