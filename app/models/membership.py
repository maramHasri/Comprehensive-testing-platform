from datetime import datetime
from enum import Enum

from app.extensions import db


class MembershipRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"
    EXAMINER = "examiner"


class MembershipStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Membership(db.Model):
    __tablename__ = "memberships"

    __table_args__ = (
        db.UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_organization"),
        db.Index("idx_user_org", "user_id", "organization_id"),
    )

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    role = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=MembershipStatus.ACTIVE.value)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    user = db.relationship("User", back_populates="memberships")
    organization = db.relationship("Organization", back_populates="memberships")