from datetime import datetime
from enum import Enum

from app.extensions import db


class ProviderType(str, Enum):
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"


class ProviderMembershipRole(str, Enum):
    ADMIN = "admin"
    INSTRUCTOR = "instructor"
    OBSERVER = "observer"
    SUPERVISOR = "supervisor"

class Provider(db.Model):
    __tablename__ = "providers"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False, default="individual")
    full_name = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")
    password = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(120), nullable=True)
    specialization = db.Column(db.String(255), nullable=True)
    years_of_experience = db.Column(db.Integer, nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    account_type = db.Column(db.String(30), nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True)
    cv = db.Column(db.String(255), nullable=True)
    linkedin_profile = db.Column(db.String(255), nullable=True)
    educational_certificates = db.Column(db.String(255), nullable=True)
    current_workplace = db.Column(db.String(255), nullable=True)
    affiliated_institution_name = db.Column(db.String(255), nullable=True)
    official_educational_certificate = db.Column(db.String(255), nullable=True)
    admin_approval = db.Column(db.Boolean, nullable=False, default=False)
    verified_affiliation_with_institution = db.Column(db.Boolean, nullable=False, default=False)
    trust_level = db.Column(db.String(20), nullable=False, default="BASIC")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    memberships = db.relationship("ProviderUser", back_populates="provider", lazy=True, cascade="all, delete-orphan")
    individual_profile = db.relationship(
        "IndividualProfile",
        back_populates="provider",
        uselist=False,
        cascade="all, delete-orphan",
    )
    organization_profile = db.relationship(
        "OrganizationProfile",
        back_populates="provider",
        uselist=False,
        cascade="all, delete-orphan",
    )
    exams = db.relationship("Exam", back_populates="provider", lazy=True, cascade="all, delete-orphan")
    organization = db.relationship("Organization", back_populates="provider", uselist=False)


class ProviderUser(db.Model):
    __tablename__ = "provider_users"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("providers.id", ondelete="CASCADE"), primary_key=True)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="provider_memberships")
    provider = db.relationship("Provider", back_populates="memberships")


class IndividualProfile(db.Model):
    __tablename__ = "individual_profiles"

    provider_id = db.Column(db.Integer, db.ForeignKey("providers.id", ondelete="CASCADE"), primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    national_id = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    provider = db.relationship("Provider", back_populates="individual_profile")


class OrganizationProfile(db.Model):
    __tablename__ = "organization_profiles"

    provider_id = db.Column(db.Integer, db.ForeignKey("providers.id", ondelete="CASCADE"), primary_key=True)
    organization_name = db.Column(db.String(255), nullable=False)
    registration_number = db.Column(db.String(120), nullable=False)
    website = db.Column(db.String(255), nullable=True)
    contact_person_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    provider = db.relationship("Provider", back_populates="organization_profile")
