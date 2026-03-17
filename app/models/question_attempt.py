from app.extensions import db
from datetime import datetime

class QuestionAttempt(db.Model):
    __tablename__ = "question_attempts"

    id = db.Column(db.Integer, primary_key=True)

    quiz_attempt_id = db.Column(
        db.Integer,
        db.ForeignKey("quiz_attempts.id"),
        nullable=False
    )

    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id"),
        nullable=False
    )

    selected_answer = db.Column(db.Text)
    is_correct = db.Column(db.Boolean)

    time_spent = db.Column(db.Integer)  # seconds
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)
