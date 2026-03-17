from app.extensions import db
from datetime import datetime

# Access levels: public (visible to all, no owner shown), protected (visible, owner shown), private (owner only)
ACCESS_PUBLIC = "public"
ACCESS_PROTECTED = "protected"
ACCESS_PRIVATE = "private"
ACCESS_TYPES = (ACCESS_PUBLIC, ACCESS_PROTECTED, ACCESS_PRIVATE)


class QuestionBank(db.Model):
    __tablename__ = "question_banks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    access_type = db.Column(db.String(20), nullable=False, default=ACCESS_PRIVATE)  # public | protected | private
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship("Question", backref="bank", lazy=True, cascade="all, delete-orphan")
