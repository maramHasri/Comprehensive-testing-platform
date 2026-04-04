"""Merge query, form, and JSON bodies for processing routes (Swagger-friendly)."""
import json

from flask import request


def merge_multipart_inputs() -> dict:
    merged: dict = {}
    merged.update(request.form.to_dict())
    merged.update(request.args.to_dict())
    body = request.get_json(silent=True)
    if isinstance(body, dict):
        merged.update(body)
    elif body is None and request.data:
        try:
            raw = json.loads(request.data.decode("utf-8-sig"))
            if isinstance(raw, dict):
                merged.update(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, AttributeError):
            pass
    if not merged.get("content_text"):
        forced = request.get_json(force=True, silent=True)
        if isinstance(forced, dict):
            merged.update(forced)
    return merged
