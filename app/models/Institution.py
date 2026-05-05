class InstitutionProfile(db.Model):
    __tablename__ = "institution_profiles"

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )

    country = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    responsible_person_name = db.Column(db.String(255), nullable=False)
    official_website = db.Column(db.String(255), nullable=True)
    logo = db.Column(db.String(255), nullable=True)

    organization = db.relationship("Organization", back_populates="institution_profile")