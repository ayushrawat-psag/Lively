import logging

import httpx

from app.core.config import Settings, get_settings
from app.email_templates import render_email_template

logger = logging.getLogger(__name__)

CM_CLASSIC_EMAIL_SEND_URL = (
    "https://api.createsend.com/api/v3.3/transactional/classicEmail/send"
)


class EmailSendError(Exception):
    """Raised when Campaign Monitor fails to accept a transactional email."""


class EmailService:
    """Sends transactional emails via Campaign Monitor classic email REST API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(
            self.settings.campaign_monitor_api_key
            and self.settings.campaign_monitor_sender_email
        )

    def send_verification_email(self, *, to_email: str, to_name: str, code: str) -> None:
        subject = "Verify your Lively account"
        context = {
            "to_name": to_name or "there",
            "code": code,
            "expire_minutes": self.settings.verification_code_expire_minutes,
        }
        html_content = render_email_template("verification.html", **context)
        text_content = render_email_template("verification.txt", **context)
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
                "Campaign Monitor is not configured "
                "(missing CAMPAIGN_MONITOR_API_KEY / CAMPAIGN_MONITOR_SENDER_EMAIL). "
                "Skipping send to %s. Subject=%s",
                to_email,
                subject,
            )
            return

        sender_name = self.settings.campaign_monitor_sender_name
        sender_email = self.settings.campaign_monitor_sender_email
        to_recipient = f"{to_name} <{to_email}>" if to_name else to_email

        payload = {
            "From": f"{sender_name} <{sender_email}>",
            "To": [to_recipient],
            "Subject": subject,
            "Html": html_content,
            "Text": text_content,
            "ConsentToTrack": "Unchanged",
            "Group": "Account Verification",
        }
        params = {}
        if self.settings.campaign_monitor_client_id:
            params["clientID"] = self.settings.campaign_monitor_client_id

        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(
                    CM_CLASSIC_EMAIL_SEND_URL,
                    json=payload,
                    params=params or None,
                    auth=(self.settings.campaign_monitor_api_key, "x"),
                )
        except httpx.HTTPError as exc:
            logger.exception("Campaign Monitor request failed for %s", to_email)
            raise EmailSendError("Failed to send verification email") from exc

        if response.status_code not in (200, 201, 202):
            logger.error(
                "Campaign Monitor rejected email to %s: status=%s body=%s",
                to_email,
                response.status_code,
                response.text,
            )
            raise EmailSendError("Failed to send verification email")

        logger.info("Verification email sent via Campaign Monitor to %s", to_email)
