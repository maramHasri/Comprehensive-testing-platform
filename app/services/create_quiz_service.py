"""Shim: localized create-quiz-from-bank lives in app.services.quiz.create_quiz_service."""
from app.services.quiz.create_quiz_service import create_quiz_from_bank

__all__ = ["create_quiz_from_bank"]
