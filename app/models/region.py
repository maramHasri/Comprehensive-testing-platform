from datetime import datetime

from app.extensions import db


class Region(db.Model):
    __tablename__ = "regions"

    __table_args__ = (
        db.UniqueConstraint("country_id", "name", name="uq_regions_country_name"),
    )

    id = db.Column(db.Integer, primary_key=True)

    country_id = db.Column(
        db.Integer,
        db.ForeignKey("countries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # اختياري: كود إداري للمنطقة (مثل CA للـ California)
    code = db.Column(db.String(10), nullable=True, index=True)

    name = db.Column(db.String(120), nullable=False, index=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # العلاقة العكسية (تطابق Country.regions)
    country = db.relationship(
        "Country",
        back_populates="regions"
    )

    def __repr__(self):
        return f"<Region {self.name} ({self.country_id})>"