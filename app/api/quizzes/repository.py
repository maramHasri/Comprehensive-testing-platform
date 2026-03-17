"""
Quizzes API repository facade.

Expose quiz-related data access functions to the API layer while delegating
implementation to the shared repositories package.
"""

from app.repositories.quize import get_user_by_id

