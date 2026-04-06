import logging
import os
import smtplib
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_TIMEOUT_SECONDS = 10


def _email_trace(message: str) -> None:
    """Visible on Render (stdout) and in app logs."""
    line = f"[EMAIL] {message}"
    logger.info("%s", line)
    print(line, flush=True)


def send_otp_email(to_email: str, otp: str, app_name: str = "quiz management system") -> bool:
    """
    Send OTP via Gmail SMTP (STARTTLS on port 587).
    Returns True on success; False on any failure (never raises).
    """
    server: smtplib.SMTP | None = None
    try:
        # Raw env (before Flask config) — helps verify .env / Render vars are visible to the process.
        print("DEBUG EMAIL:", os.getenv("GMAIL_USER"), flush=True)
        # Never print the full app password in logs (secrets leak). Length + presence only.
        _dp_env = os.getenv("GMAIL_APP_PASSWORD")
        print(
            "DEBUG PASS:",
            f"set len={len(_dp_env)}" if _dp_env else "missing",
            flush=True,
        )

        from flask import current_app

        gmail_user = (current_app.config.get("GMAIL_USER") or "").strip()
        gmail_password = current_app.config.get("GMAIL_APP_PASSWORD")
        if isinstance(gmail_password, str):
            # Google shows app passwords as "xxxx xxxx xxxx xxxx"; SMTP needs them without spaces.
            gmail_password = "".join(gmail_password.split())

        _email_trace(
            f"GMAIL_USER: {'set' if gmail_user else 'None'} "
            f"(length={len(gmail_user) if isinstance(gmail_user, str) else 0})"
        )
        _email_trace(f"GMAIL_APP_PASSWORD present: {bool(gmail_password)}")

        if not gmail_user or not gmail_password:
            _email_trace("Abort: missing GMAIL_USER or GMAIL_APP_PASSWORD")
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

        _email_trace(
            f"Connecting SMTP {SMTP_HOST}:{SMTP_PORT} (timeout={SMTP_TIMEOUT_SECONDS}s)"
        )
        server = smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=SMTP_TIMEOUT_SECONDS,
        )
        _email_trace("SMTP TCP connection established")

        server.ehlo()
        _email_trace("EHLO (before TLS) OK")

        context = ssl.create_default_context()
        server.starttls(context=context)
        _email_trace("STARTTLS OK")

        server.ehlo()
        _email_trace("EHLO (after TLS) OK")

        server.login(gmail_user, gmail_password)
        _email_trace("SMTP login (Gmail) OK")

        server.sendmail(gmail_user, to_email, msg.as_string())
        _email_trace("sendmail completed OK")

        try:
            server.quit()
        except Exception as quit_err:
            logger.warning("[EMAIL] quit() after send: %s", quit_err)
        server = None

        _email_trace("OTP email sent successfully (end of flow).")
        logger.info("OTP email sent successfully to %s", to_email)
        return True

    except Exception as e:
        err_line = f"EMAIL ERROR: {type(e).__name__}: {e}"
        logger.exception("[EMAIL] %s", err_line)
        print(f"[EMAIL] {err_line}", file=sys.stderr, flush=True)
        if server is not None:
            try:
                server.quit()
            except Exception:
                try:
                    server.close()
                except Exception:
                    pass
        return False
