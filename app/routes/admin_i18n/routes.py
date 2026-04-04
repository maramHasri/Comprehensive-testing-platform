"""
Admin-only API to manage app_messages at runtime (bonus).
Requires JWT with role claim admin.
"""
from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import get_jwt, jwt_required

from app.extensions import db
from app.repositories.message_repository import (
    clear_message_cache,
    get_message,
    upsert_app_message_row,
)
from app.utils.localization import get_current_lang

admin_i18n_ns = Namespace(
    "Admin — Localization",
    description="Create or update localized messages (admin only).",
)

upsert_parser = reqparse.RequestParser()
upsert_parser.add_argument(
    "message_key",
    type=str,
    required=True,
    location=("args", "json", "form"),
    help="Message key (e.g. QUIZ_TITLE_REQUIRED)",
)
upsert_parser.add_argument(
    "language",
    type=str,
    required=True,
    location=("args", "json", "form"),
    help="Language code (e.g. en, ar)",
)
upsert_parser.add_argument(
    "message_text",
    type=str,
    required=True,
    location=("args", "json", "form"),
    help="Translated text",
)


def _forbidden_if_not_admin():
    claims = get_jwt() or {}
    if claims.get("role") != "admin":
        return ({"message": get_message("access_denied", get_current_lang())}, 403)
    return None


@admin_i18n_ns.route("/messages")
class AdminMessagesUpsert(Resource):
    @jwt_required()
    def post(self):
        """Create or update a single message row."""
        denied = _forbidden_if_not_admin()
        if denied:
            return denied
        args = upsert_parser.parse_args()
        key = (args.get("message_key") or "").strip()
        lang = (args.get("language") or "").strip()
        text = (args.get("message_text") or "").strip()
        if not key or not lang or not text:
            return {"message": get_message("invalid_input", get_current_lang())}, 400
        try:
            upsert_app_message_row(key, lang, text)
            db.session.commit()
            clear_message_cache(key)
            return {
                "message": get_message("ADMIN_I18N_MESSAGE_SAVED", get_current_lang()),
                "message_key": key,
                "language": lang,
            }, 200
        except Exception:
            db.session.rollback()
            raise
