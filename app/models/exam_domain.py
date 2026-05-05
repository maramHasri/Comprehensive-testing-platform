from datetime import datetime
from enum import Enum

from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class ExamSessionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TERMINATED = "terminated"


class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    organization = db.relationship("Organization", backref="exams")
    sessions = db.relationship("ExamSession", back_populates="exam", lazy=True, cascade="all, delete-orphan")


class ExamSession(db.Model):
    __tablename__ = "exam_sessions"

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=ExamSessionStatus.IN_PROGRESS.value)

    exam = db.relationship("Exam", back_populates="sessions")
    user = db.relationship("User", back_populates="exam_sessions")
    logs = db.relationship("ExamSessionLog", back_populates="session", lazy=True, cascade="all, delete-orphan")


class ExamSessionLog(db.Model):
    __tablename__ = "exam_session_logs"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    event_metadata = db.Column("metadata", JSONB().with_variant(db.JSON, "sqlite"), nullable=True)

    session = db.relationship("ExamSession", back_populates="logs")
