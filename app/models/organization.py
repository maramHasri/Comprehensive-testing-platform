from datetime import datetime
from enum import Enum

from sqlalchemy import text

from app.extensions import db


class OrganizationKind(str, Enum):
    INSTITUTION = "institution"
    INDEPENDENT_TEACHER = "independent_teacher"
    PLATFORM = "platform"




class Institution(db.Model):
    __tablename__ = "institutions"

    id = db.Column(
        db.Integer,
        unique=True,
        index=True,
        nullable=False,
        server_default=text("nextval('institutions_id_seq'::regclass)"),
    )
    email = db.Column(db.String(120), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(120), nullable=False)
    country = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    responsible_person_name = db.Column(db.String(255), nullable=False)
    short_description = db.Column(db.Text, nullable=False)
    official_website_domain = db.Column(db.String(255), nullable=True)
    institutional_email = db.Column(db.String(120), nullable=True)
    logo = db.Column(db.String(255), nullable=True)
    year_of_establishment = db.Column(db.Integer, nullable=True)
    additional_program_details = db.Column(db.Text, nullable=True)
    social_links = db.Column(db.Text, nullable=True)
    official_document = db.Column(db.String(255), nullable=True)
    active_website = db.Column(db.String(255), nullable=True)
    government_reference_link = db.Column(db.String(255), nullable=True)
    admin_approval = db.Column(db.Boolean, nullable=False, default=False)
    trust_level = db.Column(db.String(20), nullable=False, default="BASIC")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    organization = db.relationship("Organization", back_populates="institution", uselist=False)


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(30), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), unique=True, nullable=True)
    admin_approval = db.Column(db.Boolean, nullable=False, default=False)
    trust_level = db.Column(db.String(20), nullable=False, default="BASIC")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    institution = db.relationship("Institution", back_populates="organization", foreign_keys=[institution_id])
    memberships = db.relationship(
        "Membership",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )