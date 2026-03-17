"""
Localization: read Accept-Language from request and provide get_localized_message.
Uses message repository for DB-backed messages; fallback to English.
"""
from flask import request


def get_current_lang() -> str:
    """
    Get language from request header Accept-Language.
    Default: en. Supports "ar", "en", "ar-EG", "en-US" etc. (uses first 2 chars).
    """
    raw = request.headers.get("Accept-Language", "en") if request else "en"
    lang = (raw or "en").strip().lower()
    if "-" in lang:
        lang = lang.split("-")[0]
    return lang[:2] if len(lang) >= 2 else "en"


def get_localized_message(message_key: str, lang: str = None) -> str:
    """
    Get user-facing message from database by key and language.
    If lang is None, uses get_current_lang() from request.
    Fallback: if translation missing for requested lang, returns English.
    """
    from app.repositories.message_repository import get_message
    if lang is None:
        lang = get_current_lang()
    return get_message(message_key, lang)


def get_localized_message_format(message_key: str, lang: str = None, **kwargs) -> str:
    """Get localized message and format with kwargs."""
    from app.repositories.message_repository import get_message_format
    if lang is None:
        lang = get_current_lang()
    return get_message_format(message_key, lang, **kwargs)
