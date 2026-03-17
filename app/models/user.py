from app.extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = "users"

    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), nullable=False)  # teacher | student

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    quizzes = db.relationship("Quiz", backref="creator", lazy=True)
    question_banks = db.relationship("QuestionBank", backref="owner", lazy=True)
    attempts = db.relationship("QuizAttempt", backref="student", lazy=True)
  # 🔹 تابع لتعيين كلمة مرور مشفرة
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # 🔹 تابع للتحقق من كلمة المرور
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)