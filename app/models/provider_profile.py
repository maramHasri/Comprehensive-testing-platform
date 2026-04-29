from datetime import datetime

from app.extensions import db


class ProviderProfile(db.Model):
    __tablename__ = "provider_profiles"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    specialization = db.Column(db.String(255), nullable=True)
    years_of_experience = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="provider_profile")
