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

    # Password reset (OTP)
    OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "60"))
    OTP_VERIFIED_WINDOW_MINUTES = int(os.getenv("OTP_VERIFIED_WINDOW_MINUTES", "15"))  # How long after verify-otp user can reset

    # Rate limiting (forgot-password)
    RATE_LIMIT_FORGOT_PASSWORD = os.getenv("RATE_LIMIT_FORGOT_PASSWORD", "7 per hour")

    # Gmail SMTP (sensitive: set in .env)
    GMAIL_USER = os.getenv("GMAIL_USER", "meesama89434@gmail.com")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "jvou ybak evxp frbm")