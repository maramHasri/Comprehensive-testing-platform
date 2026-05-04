from datetime import datetime

from app.extensions import db


class ProviderStudent(db.Model):
    __tablename__ = "provider_students"

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("providers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    provider = db.relationship("Provider", backref=db.backref("provider_students", lazy="dynamic"))
    user = db.relationship("User", backref=db.backref("provider_student_links", lazy="dynamic"))
