
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)


def send_otp_email(to_email: str, otp: str, app_name: str = "quiz management system") -> bool:
    """
    Send OTP via email. Returns True if sent successfully this function does not store it.
    """
    from flask import current_app
    try:
        gmail_user = current_app.config.get("GMAIL_USER")
        gmail_password = current_app.config.get("GMAIL_APP_PASSWORD")
        if not gmail_user or not gmail_password:
            logger.warning("Gmail credentials not configured; skipping send.")
            return False

        subject = f"{app_name} - Password Reset Code"
        body = f"""Hello,

Your password reset code is: {otp}

This code expires in {current_app.config.get('OTP_EXPIRY_MINUTES', 10)} minutes. Do not share it with anyone.

If you did not request this, please ignore this email.

—
{app_name}
"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = gmail_user
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to_email, msg.as_string())

        logger.info("OTP email sent successfully to %s", to_email)
        return True
    except Exception as e:
        logger.exception("Failed to send OTP email to %s: %s", to_email, e)
        return False
