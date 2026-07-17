import logging

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


class EmailSendError(Exception):
    """Raised when Brevo fails to accept a transactional email."""


class EmailService:
    """Sends transactional emails via Brevo REST API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.brevo_api_key and self.settings.brevo_sender_email)

    def send_verification_email(self, *, to_email: str, to_name: str, code: str) -> None:
        subject = "Verify your Lively account"
        html_content = self._verification_html(to_name=to_name, code=code)
        text_content = (
            f"Hi {to_name},\n\n"
            f"Your Lively verification code is: {code}\n\n"
            f"This code expires in {self.settings.verification_code_expire_minutes} minutes.\n"
            "If you did not create an account, you can ignore this email.\n"
        )
        self._send(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def _send(
        self,
        *,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> None:
        if not self.is_configured:
            logger.warning(
                "Brevo is not configured (missing BREVO_API_KEY / BREVO_SENDER_EMAIL). "
                "Skipping send to %s. Subject=%s",
                to_email,
                subject,
            )
            return

        payload = {
            "sender": {
                "email": self.settings.brevo_sender_email,
                "name": self.settings.brevo_sender_name,
            },
            "to": [{"email": to_email, "name": to_name or to_email}],
            "subject": subject,
            "htmlContent": html_content,
            "textContent": text_content,
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": self.settings.brevo_api_key,
        }

        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(BREVO_SEND_URL, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            logger.exception("Brevo request failed for %s", to_email)
            raise EmailSendError("Failed to send verification email") from exc

        if response.status_code not in (200, 201):
            logger.error(
                "Brevo rejected email to %s: status=%s body=%s",
                to_email,
                response.status_code,
                response.text,
            )
            raise EmailSendError("Failed to send verification email")

        logger.info("Verification email sent via Brevo to %s", to_email)

    @staticmethod
    def _verification_html(*, to_name: str, code: str) -> str:
        safe_name = to_name or "there"
        return f"""\
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #222;">
    <p>Hi {safe_name},</p>
    <p>Use this code to verify your Lively account:</p>
    <p style="font-size: 28px; font-weight: bold; letter-spacing: 4px;">{code}</p>
    <p>This code expires soon. If you did not sign up for Lively, you can ignore this email.</p>
  </body>
</html>
"""
