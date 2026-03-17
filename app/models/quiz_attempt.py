from app.extensions import db
from datetime import datetime
#حالات الاختبار :انتهى وقته  او جاري الحل  او جاهز 
class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"

    id = db.Column(db.Integer, primary_key=True)

    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime)

    status = db.Column(
        db.String(20),
        default="in_progress"  # in_progress | submitted | timeout
    )

    remaining_time = db.Column(db.Integer, nullable=False)

    score = db.Column(db.Float)

    question_attempts = db.relationship(
        "QuestionAttempt",
        backref="quiz_attempt",
        lazy=True
    )
