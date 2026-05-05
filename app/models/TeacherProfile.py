class TeacherProfile(db.Model):
    __tablename__ = "teacher_profiles"

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )

    full_name = db.Column(db.String(255), nullable=False)
    specialization = db.Column(db.String(255), nullable=True)
    years_of_experience = db.Column(db.Integer, nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    country = db.Column(db.String(120), nullable=True)

    cv = db.Column(db.String(255), nullable=True)
    linkedin_profile = db.Column(db.String(255), nullable=True)
    educational_certificates = db.Column(db.String(255), nullable=True)

    organization = db.relationship("Organization", back_populates="teacher_profile")