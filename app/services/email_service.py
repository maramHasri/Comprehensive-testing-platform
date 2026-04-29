import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    gmail_user = (current_app.config.get("GMAIL_USER") or "").strip()
    gmail_app_password = (current_app.config.get("GMAIL_APP_PASSWORD") or "").replace(" ", "")
    smtp_host = (current_app.config.get("SMTP_HOST") or "smtp.gmail.com").strip()
    smtp_port = int(current_app.config.get("SMTP_PORT") or 587)
    if not gmail_user or not gmail_app_password:
        logger.error("[SMTP] Missing GMAIL_USER or GMAIL_APP_PASSWORD in environment.")
        return False
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = gmail_user
    message["To"] = to_email
    message.attach(MIMEText(html_content, "html", "utf-8"))
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(gmail_user, gmail_app_password)
            server.sendmail(gmail_user, [to_email], message.as_string())
        logger.info("[SMTP] Email sent to %s", to_email)
        return True
    except smtplib.SMTPException as err:
        logger.exception("[SMTP] SMTP error: %s", err)
        return False
    except OSError as err:
        logger.exception("[SMTP] OS error: %s", err)
        return False
