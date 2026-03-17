"""
Stores localized user-facing messages. Key + language identify a message.
Used for multilingual responses (e.g. en, ar).
"""
from app.extensions import db


class AppMessage(db.Model):
    __tablename__ = "app_messages"

    id = db.Column(db.Integer, primary_key=True)
    message_key = db.Column(db.String(100), nullable=False, index=True)
    language = db.Column(db.String(10), nullable=False, index=True)  # en, ar, etc.
    message_text = db.Column(db.Text, nullable=False)

    __table_args__ = (db.UniqueConstraint("message_key", "language", name="uq_app_message_key_lang"),)
