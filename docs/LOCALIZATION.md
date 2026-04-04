# Localization (`app_messages`)

## Overview

- **Table:** `app_messages` (`message_key`, `language`, `message_text`), unique on `(message_key, language)`.
- **Catalog:** `app/localization/catalog.py` — single source for seed data and English fallbacks when the DB is empty.
- **API helper:** `get_message(message_key, language)` in `app/repositories/message_repository.py` (cached).
- **Request language:** `Accept-Language` header (e.g. `ar`, `en-US` → `en`); use `get_current_lang()` from `app/utils/localization.py`.

## Run the seed script

From the **project root** (where `run.py` lives), with `.env` loaded (`DATABASE_URL` set):

```bash
python scripts/seed_app_messages.py
```

The script is **idempotent**: re-running updates changed texts and inserts missing rows.

After seeding, restart the app if you rely on long-lived workers (cache is cleared at end of seed).

## Where files live

| Path | Role |
|------|------|
| `app/localization/catalog.py` | All predefined keys + `en` / `ar` strings |
| `scripts/seed_app_messages.py` | CLI that upserts catalog into the DB |
| `app/repositories/message_repository.py` | `get_message`, `get_message_format`, cache, `clear_message_cache`, `upsert_app_message_row` |
| `app/utils/localization.py` | `get_current_lang`, delegates to `get_message` |

## Add new messages later

1. Add a key and translations to `MESSAGE_CATALOG` in `app/localization/catalog.py`.
2. Run `python scripts/seed_app_messages.py`.
3. Use the key in services/routes: `get_message("YOUR_KEY", get_current_lang())`.

Optional: use **POST** `/api/admin/messages` (JWT, **admin** role) with `message_key`, `language`, `message_text` to update the DB without redeploying the catalog file.

## Use in Flask routes

```python
from app.utils.localization import get_current_lang
from app.repositories.message_repository import get_message, get_message_format

def get(self):
    lang = get_current_lang()
    return {"message": get_message("quiz_created", lang)}, 200

# With placeholders (must exist in DB/catalog text):
return {"message": get_message_format("QUIZ_BANK_TOO_FEW_QUESTIONS", lang, count=3)}, 400
```

Clients should send `Accept-Language: ar` or `en` for the desired language.

## Admin API (bonus)

- **POST** `/api/admin/messages`
- **Header:** `Authorization: Bearer <JWT>` with `role: admin` in token claims.
- **Body (JSON or form):** `message_key`, `language`, `message_text`

Invalidates cache for that `message_key` after save.
