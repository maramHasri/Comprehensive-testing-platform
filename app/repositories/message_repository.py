"""
Localized user-facing messages: DB-backed (app_messages) with catalog fallbacks and in-memory cache.
"""
from __future__ import annotations

import threading
from typing import Any

from app.extensions import db
from app.models import AppMessage
from app.localization.catalog import english_fallbacks

# Last-resort string when key is unknown (not in DB, not in catalog).
DEFAULT_MISSING_MESSAGE = "Message not available."

# In-memory cache: (message_key, normalized_lang) -> resolved text
_message_cache: dict[tuple[str, str], str] = {}
_cache_lock = threading.Lock()


def _normalize_language(language: str | None) -> str:
    lang = (language or "en").strip().lower()
    if len(lang) > 2:
        lang = lang[:2]
    return lang if lang else "en"


# English strings from catalog (used when DB has no row yet)
_FALLBACK_EN: dict[str, str] = english_fallbacks()


def clear_message_cache(message_key: str | None = None) -> None:
    """
    Invalidate cache after seeding or admin updates.
    If message_key is None, clear entire cache; otherwise drop entries for that key only.
    """
    global _message_cache
    with _cache_lock:
        if message_key is None:
            _message_cache = {}
        else:
            _message_cache = {
                k: v for k, v in _message_cache.items() if k[0] != message_key
            }


def get_message_row(message_key: str, language: str):
    lang = _normalize_language(language)
    return AppMessage.query.filter_by(
        message_key=message_key,
        language=lang,
    ).first()


def get_message_row_fallback(message_key: str):
    return AppMessage.query.filter_by(
        message_key=message_key,
        language="en",
    ).first()


def _resolve_message_text(message_key: str, language: str) -> str:
    """
    Resolve text without using the cache (single source of truth for lookup order).
    Order: requested lang in DB -> English in DB -> catalog English -> default.
    """
    lang = _normalize_language(language)
    row = get_message_row(message_key, lang)
    if row:
        return row.message_text
    if lang != "en":
        fb = get_message_row_fallback(message_key)
        if fb:
            return fb.message_text
    if message_key in _FALLBACK_EN:
        return _FALLBACK_EN[message_key]
    return DEFAULT_MISSING_MESSAGE


def get_message(message_key: str, language: str) -> str:
    """
    Return translated message for key and language.

    - Reads from DB first, then English DB row, then static English catalog, then DEFAULT_MISSING_MESSAGE.
    - Result is cached per (message_key, language) to reduce DB hits.
    """
    lang = _normalize_language(language)
    cache_key = (message_key, lang)
    with _cache_lock:
        if cache_key in _message_cache:
            return _message_cache[cache_key]
    text = _resolve_message_text(message_key, lang)
    with _cache_lock:
        _message_cache[cache_key] = text
    return text


def get_message_format(message_key: str, language: str, **kwargs: Any) -> str:
    text = get_message(message_key, language)
    try:
        return text.format(**kwargs)
    except KeyError:
        return text


def upsert_app_message_row(message_key: str, language: str, message_text: str) -> AppMessage:
    """
    Insert or update one row (used by seed script and admin API).
    Caller should commit session and call clear_message_cache(message_key).
    """
    lang = _normalize_language(language)
    row = AppMessage.query.filter_by(message_key=message_key, language=lang).first()
    if row:
        row.message_text = message_text
        return row
    row = AppMessage(
        message_key=message_key,
        language=lang,
        message_text=message_text,
    )
    db.session.add(row)
    return row
