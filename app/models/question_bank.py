from app.extensions import db
from datetime import datetime

# Access levels: public (visible to all, no owner shown), protected (visible, owner shown), private (owner only)
ACCESS_PUBLIC = "public"
ACCESS_PROTECTED = "protected"
ACCESS_PRIVATE = "private"
ACCESS_TYPES = (ACCESS_PUBLIC, ACCESS_PROTECTED, ACCESS_PRIVATE)


class BankTopic(db.Model):
    """A label within a question bank used to classify questions (unique name per bank)."""

    __tablename__ = "bank_topics"
    __table_args__ = (db.UniqueConstraint("bank_id", "name", name="uq_bank_topics_bank_name"),)

    id = db.Column(db.Integer, primary_key=True)
    bank_id = db.Column(db.Integer, db.ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship("Question", back_populates="topic", lazy=True)
    question_bank = db.relationship("QuestionBank", back_populates="bank_topics")


class BankLevel(db.Model):
    __tablename__ = "bank_levels"
    __table_args__ = (db.UniqueConstraint("bank_id", "name", name="uq_bank_levels_bank_name"),)

    id = db.Column(db.Integer, primary_key=True)
    bank_id = db.Column(db.Integer, db.ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship("Question", back_populates="level", lazy=True)
    question_bank = db.relationship("QuestionBank", back_populates="bank_levels")


class BankRepeatedLevel(db.Model):
    __tablename__ = "bank_repeated_levels"
    __table_args__ = (db.UniqueConstraint("bank_id", "name", name="uq_bank_repeated_levels_bank_name"),)

    id = db.Column(db.Integer, primary_key=True)
    bank_id = db.Column(db.Integer, db.ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship("Question", back_populates="repeated_level", lazy=True)
    question_bank = db.relationship("QuestionBank", back_populates="bank_repeated_levels")


class QuestionBank(db.Model):
    __tablename__ = "question_banks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # 1) Visibility concern
    is_public = db.Column(db.Boolean, nullable=False, default=False)
    # 2) Pricing concern
    is_paid = db.Column(db.Boolean, nullable=False, default=False)
    base_price = db.Column(db.Float, nullable=False, default=0.0)
    # 3) Access / permissions concern
    access_type = db.Column(db.String(20), nullable=False, default=ACCESS_PRIVATE)  # public | protected | private
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship("Question", backref="bank", lazy=True, cascade="all, delete-orphan")
    versions = db.relationship("BankVersion", backref="bank", lazy=True, cascade="all, delete-orphan")
    purchases = db.relationship("Purchase", backref="bank", lazy=True, cascade="all, delete-orphan")
    bank_questions = db.relationship("BankQuestion", backref="bank", lazy=True, cascade="all, delete-orphan")
    bank_topics = db.relationship(
        "BankTopic",
        back_populates="question_bank",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="BankTopic.sort_order",
    )
    bank_levels = db.relationship(
        "BankLevel",
        back_populates="question_bank",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="BankLevel.sort_order",
    )
    bank_repeated_levels = db.relationship(
        "BankRepeatedLevel",
        back_populates="question_bank",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="BankRepeatedLevel.sort_order",
    )


class BankVersion(db.Model):
    __tablename__ = "bank_versions"

    id = db.Column(db.Integer, primary_key=True)
    bank_id = db.Column(db.Integer, db.ForeignKey("question_banks.id"), nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False, default=0.0)
    update_type = db.Column(db.String(10), nullable=False, default="minor")  # minor | major
    question_count = db.Column(db.Integer, nullable=False, default=0)
    topic_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_major_update = db.Column(db.Boolean, nullable=False, default=False)

    purchases = db.relationship("Purchase", backref="version", lazy=True)


class Purchase(db.Model):
    __tablename__ = "purchases"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    bank_id = db.Column(db.Integer, db.ForeignKey("question_banks.id"), nullable=True, index=True)
    bank_version_id = db.Column(db.Integer, db.ForeignKey("bank_versions.id"), nullable=False, index=True)
    price_paid = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class Offer(db.Model):
    __tablename__ = "offers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    discount_percentage = db.Column(db.Float, nullable=False, default=0.0)
    valid_from = db.Column(db.DateTime, nullable=False)
    valid_to = db.Column(db.DateTime, nullable=False)
    applies_to_first_purchase = db.Column(db.Boolean, nullable=False, default=False)
    applies_to_upgrade = db.Column(db.Boolean, nullable=False, default=False)

    def is_active(self, at_time=None):
        at_time = at_time or datetime.utcnow()
        return self.valid_from <= at_time <= self.valid_to
