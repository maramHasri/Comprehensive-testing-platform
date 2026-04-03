"""
Localization service:
- Reads request language
- Applies fallback logic
- Formats messages
"""

from flask import request
from app.repositories.message_repository import get_message_row, get_message_row_fallback


def get_current_lang() -> str:
    """
    Extract language from request header.
    Example: en-US -> en
    """
    raw = request.headers.get("Accept-Language", "en") if request else "en"

    lang = (raw or "en").strip().lower()

    if "-" in lang:
        lang = lang.split("-")[0]

    return lang[:2] if len(lang) >= 2 else "en"


def get_localized_message(message_key: str, lang: str = None) -> str:
    """
    Get message with fallback to English.
    """
    if lang is None:
        lang = get_current_lang()

    row = get_message_row(message_key, lang)

    if row:
        return row.message_text

    # fallback to English
    if lang != "en":
        fallback = get_message_row_fallback(message_key)
        if fallback:
            return fallback.message_text

    return message_key


def get_localized_message_format(message_key: str, lang: str = None, **kwargs) -> str:
    """
    Get localized message and format placeholders.
    Example: "Hello {name}"
    """
    text = get_localized_message(message_key, lang)

    try:
        return text.format(**kwargs)
    except KeyError:
        return text