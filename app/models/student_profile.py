from datetime import datetime

from app.extensions import db


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    university = db.Column(db.String(255), nullable=True)
    student_number = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="student_profile")
