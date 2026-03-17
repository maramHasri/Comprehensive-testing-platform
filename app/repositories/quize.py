"""
Quizzes data access. No business logic.
"""
from app.models import User


def get_user_by_id(user_id: int):
    return User.query.get(user_id)
