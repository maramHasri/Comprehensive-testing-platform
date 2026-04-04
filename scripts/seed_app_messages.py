#!/usr/bin/env python3
"""
Idempotent seed for app_messages (localized strings).

Usage (from project root):
  python scripts/seed_app_messages.py

Requires DATABASE_URL and valid credentials in .env (same as flask run).

Safe to run multiple times: upserts rows by (message_key, language).
"""
from __future__ import annotations

import os
import sys

# Project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    from app import create_app
    from app.extensions import db
    from app.localization.catalog import MESSAGE_CATALOG
    from app.repositories.message_repository import clear_message_cache, upsert_app_message_row

    app = create_app()
    with app.app_context():
        total = 0
        for message_key, translations in MESSAGE_CATALOG.items():
            for language_code, message_text in translations.items():
                upsert_app_message_row(message_key, language_code, message_text)
                total += 1
        db.session.commit()
        clear_message_cache()
        print(f"Seeded/updated {total} message rows ({len(MESSAGE_CATALOG)} keys).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
