"""
Browser-oriented email verification: HTML pages, redirects, and copy for link flows.

JSON APIs stay in ``routes.py``; this module builds ``text/html`` for ``GET /auth/verify/<token>``.
"""
from dataclasses import dataclass
from html import escape

from flask import current_app

from app.repositories.message_repository import get_message
from app.services.auth_service import ActivationLinkOutcome, process_activation_link_token
from app.utils.localization import get_current_lang


def _post_verify_redirect_url() -> str:
    explicit = (current_app.config.get("FRONTEND_POST_VERIFY_REDIRECT_URL") or "").strip()
    if explicit:
        return explicit
    base = (current_app.config.get("FRONTEND_BASE_URL") or current_app.config.get("APP_BASE_URL") or "").rstrip(
        "/"
    )
    return f"{base}/dashboard" if base else "/dashboard"


def _resend_api_url() -> str:
    api_base = (current_app.config.get("APP_BASE_URL") or "").rstrip("/")
    return f"{api_base}/auth/resend-verification" if api_base else "/auth/resend-verification"


def _page_html(title: str, body: str, meta_refresh_seconds: int | None, meta_refresh_url: str | None) -> str:
    meta = ""
    if meta_refresh_seconds is not None and meta_refresh_url:
        safe_url = escape(meta_refresh_url, quote=True)
        meta = f'<meta http-equiv="refresh" content="{int(meta_refresh_seconds)};url={safe_url}">'
    redirect_js = ""
    if meta_refresh_url and meta_refresh_seconds:
        safe_js = escape(meta_refresh_url, quote=True).replace("'", "\\'")
        redirect_js = f"""
        <script>
          setTimeout(function () {{ window.location.replace('{safe_js}'); }}, {int(meta_refresh_seconds * 1000)});
        </script>"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {meta}
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background: #f3f4f6; margin: 0; padding: 32px 16px; }}
    .card {{ max-width: 520px; margin: 0 auto; background: #fff; border-radius: 12px;
      padding: 28px 24px; box-shadow: 0 8px 24px rgba(0,0,0,.08); }}
    h1 {{ font-size: 1.25rem; margin: 0 0 12px; color: #111827; }}
    p {{ color: #4b5563; line-height: 1.55; margin: 0 0 12px; }}
    a {{ color: #2563eb; }}
    .muted {{ font-size: 0.875rem; color: #6b7280; }}
    code {{ font-size: 0.8rem; background: #f3f4f6; padding: 2px 6px; border-radius: 4px; }}
  </style>
</head>
<body>
  <div class="card">
    {body}
  </div>
{redirect_js}
</body>
</html>"""


@dataclass(frozen=True)
class VerificationPage:
    """Pieces for the verify-link HTTP response."""
    html: str
    status_code: int


def build_email_verification_page(token: str | None) -> VerificationPage:
    """
    Run activation logic and return HTML (success with delayed redirect, or a safe error page).

    Uses the same ``process_activation_link_token`` rules as the JSON verify endpoint.
    """
    lang = get_current_lang()
    outcome = process_activation_link_token(token)
    redirect_url = _post_verify_redirect_url()
    resend_url = escape(_resend_api_url())
    if outcome == ActivationLinkOutcome.ACTIVATED:
        title = get_message("AUTH_PAGE_VERIFY_SUCCESS_TITLE", lang)
        msg = get_message("AUTH_PAGE_VERIFY_SUCCESS_BODY", lang)
        body = (
            f"<h1>{escape(title)}</h1><p>{escape(msg)}</p>"
            f"<p class=\"muted\">{escape(get_message('AUTH_PAGE_REDIRECTING', lang))}</p>"
        )
        html = _page_html(title, body, meta_refresh_seconds=3, meta_refresh_url=redirect_url)
        return VerificationPage(html=html, status_code=200)
    if outcome == ActivationLinkOutcome.ALREADY_VERIFIED:
        title = get_message("AUTH_PAGE_VERIFY_ALREADY_TITLE", lang)
        msg = get_message("AUTH_PAGE_VERIFY_ALREADY_BODY", lang)
        body = (
            f"<h1>{escape(title)}</h1><p>{escape(msg)}</p>"
            f"<p class=\"muted\">{escape(get_message('AUTH_PAGE_REDIRECTING', lang))}</p>"
        )
        html = _page_html(title, body, meta_refresh_seconds=3, meta_refresh_url=redirect_url)
        return VerificationPage(html=html, status_code=200)
    if outcome == ActivationLinkOutcome.EXPIRED:
        title = get_message("AUTH_PAGE_VERIFY_EXPIRED_TITLE", lang)
        msg = get_message("AUTH_PAGE_VERIFY_EXPIRED_BODY", lang)
        hint = escape(get_message("AUTH_PAGE_RESEND_INSTRUCTION", lang))
        body = f"<h1>{escape(title)}</h1><p>{escape(msg)}</p><p class=\"muted\">{hint} <code>{resend_url}</code></p>"
        html = _page_html(title, body, meta_refresh_seconds=None, meta_refresh_url=None)
        return VerificationPage(html=html, status_code=400)
    if outcome in (ActivationLinkOutcome.INVALID, ActivationLinkOutcome.USER_MISSING):
        title = get_message("AUTH_PAGE_VERIFY_INVALID_TITLE", lang)
        msg = get_message("AUTH_PAGE_VERIFY_INVALID_BODY", lang)
        hint = escape(get_message("AUTH_PAGE_RESEND_INSTRUCTION", lang))
        body = f"<h1>{escape(title)}</h1><p>{escape(msg)}</p><p class=\"muted\">{hint} <code>{resend_url}</code></p>"
        html = _page_html(title, body, meta_refresh_seconds=None, meta_refresh_url=None)
        return VerificationPage(html=html, status_code=400)
    title = get_message("AUTH_PAGE_VERIFY_MISSING_TITLE", lang)
    msg = get_message("AUTH_PAGE_VERIFY_MISSING_BODY", lang)
    body = f"<h1>{escape(title)}</h1><p>{escape(msg)}</p>"
    html = _page_html(title, body, meta_refresh_seconds=None, meta_refresh_url=None)
    return VerificationPage(html=html, status_code=400)
