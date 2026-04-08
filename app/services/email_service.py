import logging

import requests
from flask import current_app

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
REQUEST_TIMEOUT_SECONDS = 10


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    api_key = current_app.config.get("RESEND_API_KEY")
    from_email = current_app.config.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    if not api_key:
        logger.error("[RESEND] Missing RESEND_API_KEY in environment.")
        return False

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_content,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            RESEND_API_URL,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if 200 <= response.status_code < 300:
            logger.info("[RESEND] Email sent to %s (status=%s)", to_email, response.status_code)
            return True
        logger.error(
            "[RESEND] Failed status=%s body=%s",
            response.status_code,
            response.text,
        )
        return False
    except requests.RequestException as e:
        logger.exception("[RESEND] Request error: %s", e)
        return False
