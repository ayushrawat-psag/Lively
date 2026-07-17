from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.services.email_service import EmailSendError, EmailService


def test_is_configured_false_without_credentials() -> None:
    settings = Settings(
        brevo_api_key="",
        brevo_sender_email="",
        include_verification_code_in_response=True,
    )
    assert EmailService(settings).is_configured is False


def test_is_configured_true_with_credentials() -> None:
    settings = Settings(
        brevo_api_key="xkeysib-test",
        brevo_sender_email="noreply@example.com",
        brevo_sender_name="Lively",
    )
    assert EmailService(settings).is_configured is True


def test_send_skips_when_not_configured() -> None:
    settings = Settings(brevo_api_key="", brevo_sender_email="")
    # Should not raise
    EmailService(settings).send_verification_email(
        to_email="user@example.com",
        to_name="User",
        code="1234",
    )


def test_send_success_via_brevo() -> None:
    settings = Settings(
        brevo_api_key="xkeysib-test",
        brevo_sender_email="noreply@example.com",
        brevo_sender_name="Lively",
    )
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.text = '{"messageId":"1"}'

    with patch("app.services.email_service.httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = mock_response
        EmailService(settings).send_verification_email(
            to_email="user@example.com",
            to_name="User",
            code="4321",
        )
        client.post.assert_called_once()
        args, kwargs = client.post.call_args
        assert args[0] == "https://api.brevo.com/v3/smtp/email"
        assert kwargs["headers"]["api-key"] == "xkeysib-test"
        assert kwargs["json"]["to"][0]["email"] == "user@example.com"
        assert "4321" in kwargs["json"]["htmlContent"]


def test_send_raises_on_brevo_error_status() -> None:
    settings = Settings(
        brevo_api_key="xkeysib-test",
        brevo_sender_email="noreply@example.com",
    )
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "unauthorized"

    with patch("app.services.email_service.httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = mock_response
        with pytest.raises(EmailSendError):
            EmailService(settings).send_verification_email(
                to_email="user@example.com",
                to_name="User",
                code="9999",
            )


def test_send_raises_on_http_transport_error() -> None:
    settings = Settings(
        brevo_api_key="xkeysib-test",
        brevo_sender_email="noreply@example.com",
    )
    with patch("app.services.email_service.httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.post.side_effect = httpx.ConnectError("boom")
        with pytest.raises(EmailSendError):
            EmailService(settings).send_verification_email(
                to_email="user@example.com",
                to_name="User",
                code="1111",
            )
