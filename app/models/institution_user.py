from datetime import datetime

from app.extensions import db

INSTITUTION_USER_ROLES: tuple[str, ...] = ("admin", "instructor", "supervisor", "observer")


class InstitutionUser(db.Model):
    __tablename__ = "institution_users"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="institution_memberships")
    institution = db.relationship("Institution", back_populates="institution_memberships")
