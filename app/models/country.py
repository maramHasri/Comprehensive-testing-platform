from datetime import datetime

from app.extensions import db


class Country(db.Model):
    __tablename__ = "countries"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(3), nullable=False, unique=True, index=True)
    name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    regions = db.relationship(
        "Region",
        back_populates="country",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Region.name.asc()",
    )


class Region(db.Model):
    __tablename__ = "regions"
    __table_args__ = (db.UniqueConstraint("country_id", "name", name="uq_regions_country_name"),)

    id = db.Column(db.Integer, primary_key=True)
    country_id = db.Column(db.Integer, db.ForeignKey("countries.id", ondelete="CASCADE"), nullable=False, index=True)
    code = db.Column(db.String(10), nullable=True, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    country = db.relationship("Country", back_populates="regions")
