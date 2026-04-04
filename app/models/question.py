from app.extensions import db
from datetime import datetime

class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)

#اذا كان السؤال ينتمي لبنك اسئلة معين او نريد ادراجه ضمن كويز ايضا 
    # Deprecated in favor of bank_version_id for versioned banks.
    bank_id = db.Column(db.Integer, db.ForeignKey("question_banks.id"), nullable=True)
    topic_id = db.Column(
        db.Integer,
        db.ForeignKey("bank_topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    bank_version_id = db.Column(db.Integer, db.ForeignKey("bank_versions.id"), nullable=True, index=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    original_question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=True, index=True)

    type = db.Column(db.String(50), nullable=False)  # و نوع السؤال
    content = db.Column(db.Text, nullable=False)    # نص السؤال
    hint = db.Column(db.Text)

    #   علامة السؤال:و ممكن تكون ثابتة  على مستوى السؤال و ممكن  تتغير  على مستوى الكويز  
    # و هذا يحدده اذا اختار المستخدم ان تكون العلامات مقسمة بالتساوي  على مستوى الكويز ,انظر موديل الكويز 

    points = db.Column(db.Float, default=1.0)       
    base_time = db.Column(db.Integer, nullable=True)  # و كذا وقت السؤال ممكن يكون ثابت او يتغير حسب الكويز

    order_index = db.Column(db.Integer, nullable=True)  # ترتيب السؤال ضمن الكويز

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    quiz_questions = db.relationship("QuizQuestion", backref="question", lazy=True)
    choices = db.relationship("Choice", backref="question", cascade="all, delete-orphan")
    source_question = db.relationship("Question", remote_side=[id], backref="derived_questions", lazy=True)
    bank_links = db.relationship("BankQuestion", backref="question", lazy=True, cascade="all, delete-orphan")
    topic = db.relationship("BankTopic", back_populates="questions")
    attribution = db.relationship(
        "QuestionAttribution",
        backref="question",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="QuestionAttribution.question_id",
    )


#الخيارات الخاصة بسؤال معين
class Choice(db.Model):
    __tablename__ = "choices"
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)


class BankQuestion(db.Model):
    __tablename__ = "bank_questions"

    id = db.Column(db.Integer, primary_key=True)
    bank_id = db.Column(db.Integer, db.ForeignKey("question_banks.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False, index=True)


class QuestionAttribution(db.Model):
    __tablename__ = "question_attributions"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False, unique=True, index=True)
    original_question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False, index=True)
    original_bank_id = db.Column(db.Integer, db.ForeignKey("question_banks.id"), nullable=False, index=True)
    original_owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
