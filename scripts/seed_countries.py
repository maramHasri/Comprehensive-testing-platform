import ast
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.models import Country


def parse_countries_payload(raw_text: str) -> list[dict]:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        # Support JS-style objects like: {name: 'Syria', code: 'SY'}
        normalized = re.sub(r"([{\[,]\s*)([A-Za-z_]\w*)\s*:", r"\1'\2':", raw_text)
        data = ast.literal_eval(normalized)
    if not isinstance(data, list):
        raise ValueError("countries payload must be a list")
    rows: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip().upper()
        name = str(item.get("name") or "").strip()
        if not code or not name:
            continue
        rows.append({"code": code, "name": name})
    return rows


def upsert_countries(rows: list[dict]) -> tuple[int, int]:
    inserted = 0
    updated = 0
    for row in rows:
        existing = Country.query.filter_by(code=row["code"]).first()
        if existing is None:
            db.session.add(Country(code=row["code"], name=row["name"]))
            inserted += 1
            continue
        if existing.name != row["name"]:
            existing.name = row["name"]
            updated += 1
    db.session.commit()
    return inserted, updated


def main() -> None:
    app = create_app()
    with app.app_context():
        countries_file = Path("countries.json")
        if not countries_file.exists():
            raise FileNotFoundError("countries.json not found in project root.")
        raw_text = countries_file.read_text(encoding="utf-8")
        rows = parse_countries_payload(raw_text)
        inserted, updated = upsert_countries(rows)
        print(f"countries processed={len(rows)} inserted={inserted} updated={updated}")


if __name__ == "__main__":
    main()
