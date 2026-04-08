import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY"))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_SECONDS", str(7 * 24 * 3600)))
    )  # 7 days default
    EMAIL_VERIFY_TOKEN_EXPIRY_SECONDS = int(
        os.getenv("EMAIL_VERIFY_TOKEN_EXPIRY_SECONDS", str(30 * 60))
    )  # 30 minutes default
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000")
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")