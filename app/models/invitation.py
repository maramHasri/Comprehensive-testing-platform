from datetime import datetime
import uuid

from app.extensions import db


class Invitation(db.Model):
    __tablename__ = "invitations"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    sender_type = db.Column(db.String(20), nullable=False)
    sender_id = db.Column(db.Integer, nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False, default="student")
    max_uses = db.Column(db.Integer, nullable=False, default=1)
    used_count = db.Column(db.Integer, nullable=False, default=0)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
