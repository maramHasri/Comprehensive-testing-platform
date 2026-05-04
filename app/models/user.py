from app.extensions import db
from datetime import datetime
from flask_bcrypt import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column("name", db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True)
    country = db.Column(db.String(50), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    two_factor_enabled = db.Column(db.Boolean, nullable=False, default=False)
    two_factor_secret = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    roles = db.relationship("Role", secondary="user_roles", back_populates="users", lazy="selectin")
    memberships = db.relationship(
        "Membership",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    provider_memberships = db.relationship("ProviderUser", back_populates="user", lazy="selectin")

    # Profiles
    student_profile = db.relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    provider_profile = db.relationship(
        "ProviderProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Core relations
    exam_sessions = db.relationship("ExamSession", back_populates="user", lazy=True)
    quizzes = db.relationship("Quiz", backref="creator", lazy=True)
    question_banks = db.relationship("QuestionBank", backref="owner", lazy=True)
    attempts = db.relationship("QuizAttempt", backref="student", lazy=True)
    purchases = db.relationship("Purchase", backref="user", lazy=True, cascade="all, delete-orphan")

    # Auth
    def set_password(self, password):
        self.password_hash = generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Aliases
    @property
    def name(self):
        return self.full_name

    @name.setter
    def name(self, value):
        self.full_name = value

    @property
    def role(self) -> str:
        from app.utils.iam_helpers import infer_primary_legacy_role

        return infer_primary_legacy_role(self)

    @property
    def is_verified(self):
        return self.is_active

    @is_verified.setter
    def is_verified(self, value):
        self.is_active = bool(value)

    # Business helpers
    def has_purchased(self, bank):
        from app.models.question_bank import Purchase

        return (
            Purchase.query.filter(
                Purchase.user_id == self.id,
                Purchase.bank_id == bank.id,
            ).first()
            is not None
        )

    def has_old_version(self, bank, version):
        from app.models.question_bank import Purchase

        return (
            Purchase.query.filter(
                Purchase.user_id == self.id,
                Purchase.bank_id == bank.id,
                Purchase.bank_version_id != version.id,
            ).first()
            is not None
        )