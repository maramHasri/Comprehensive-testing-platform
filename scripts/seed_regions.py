import json

from app.extensions import db
from app.models import Country, Region


def seed_regions_from_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data["regions"]:
        country_id = item["country_id"]

        # تأكد أن الدولة موجودة
        country = Country.query.get(country_id)
        if not country:
            print(f"Country {country_id} not found, skipping")
            continue

        for name in item["regions"]:
            exists = Region.query.filter_by(
                country_id=country_id,
                name=name
            ).first()

            if not exists:
                db.session.add(
                    Region(
                        country_id=country_id,
                        name=name
                    )
                )

    db.session.commit()
    print("Regions seeded successfully!")