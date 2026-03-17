from app.extensions import db
from datetime import datetime
import uuid

class Quiz(db.Model):
    __tablename__ = "quizzes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Timing: optional window and duration
    start_at = db.Column(db.DateTime, nullable=True)   # when quiz becomes available (null = immediate)
    end_at = db.Column(db.DateTime, nullable=True)    # when quiz closes (optional)
    total_time_seconds = db.Column(db.Integer, nullable=True)  # global duration in seconds (null if per_question only)

    # Scoring
    total_score = db.Column(db.Float, nullable=False, default=100.0)

    # Options
    equally_weighted = db.Column(db.Boolean, default=True)   # score_per_question = total_score / num_questions
    free_navigation = db.Column(db.Boolean, default=True)   # true = jump any question; false = sequential
    timed_scope = db.Column(db.String(20), default="quiz")   # "quiz" | "question" | "none"

    # Lifecycle: draft by default; students cannot access draft
    status = db.Column(db.String(20), default="draft", nullable=False)  # "draft" | "published"

    access_code = db.Column(
        db.String(36),
        unique=True,
        default=lambda: str(uuid.uuid4())
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship("QuizQuestion", backref="quiz", lazy=True)
    direct_questions = db.relationship("Question", backref="quiz", lazy=True, foreign_keys="Question.quiz_id")
    attempts = db.relationship("QuizAttempt", backref="quiz", lazy=True)


class QuizQuestion(db.Model):
    __tablename__ = "quiz_questions"

    id = db.Column(db.Integer, primary_key=True)

    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)

    order = db.Column(db.Integer, nullable=False)
