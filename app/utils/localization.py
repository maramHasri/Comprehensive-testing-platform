"""
Localization helpers: request language + delegated message resolution (cached in message_repository).
"""

from flask import request

from app.localization.message_service import get_message, get_message_format


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


def get_localized_message(message_key: str, lang: str | None = None) -> str:
    """
    Same resolution as get_message (DB + English fallback + catalog + default).
    Uses in-memory cache in message_repository.
    """
    if lang is None:
        lang = get_current_lang()
    return get_message(message_key, lang)


def get_localized_message_format(message_key: str, lang: str | None = None, **kwargs) -> str:
    """Localized message with str.format placeholders."""
    if lang is None:
        lang = get_current_lang()
    return get_message_format(message_key, lang, **kwargs)
