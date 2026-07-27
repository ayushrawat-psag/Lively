from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.services.email_service import (
    CM_CLASSIC_EMAIL_SEND_URL,
    EmailSendError,
    EmailService,
)


def test_is_configured_false_without_credentials() -> None:
    settings = Settings(
        campaign_monitor_api_key="",
        campaign_monitor_sender_email="",
        include_verification_code_in_response=True,
    )
    assert EmailService(settings).is_configured is False


def test_is_configured_true_with_credentials() -> None:
    settings = Settings(
        campaign_monitor_api_key="cm-test-key",
        campaign_monitor_sender_email="noreply@example.com",
        campaign_monitor_sender_name="Lively",
    )
    assert EmailService(settings).is_configured is True


def test_send_skips_when_not_configured() -> None:
    settings = Settings(campaign_monitor_api_key="", campaign_monitor_sender_email="")
    # Should not raise
    EmailService(settings).send_verification_email(
        to_email="user@example.com",
        to_name="User",
        code="1234",
    )


def test_send_success_via_campaign_monitor() -> None:
    settings = Settings(
        campaign_monitor_api_key="cm-test-key",
        campaign_monitor_sender_email="noreply@example.com",
        campaign_monitor_sender_name="Lively",
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '[{"MessageID":"1","Status":"Accepted"}]'

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
        assert args[0] == CM_CLASSIC_EMAIL_SEND_URL
        assert kwargs["auth"] == ("cm-test-key", "x")
        assert kwargs["json"]["From"] == "Lively <noreply@example.com>"
        assert kwargs["json"]["To"] == ["User <user@example.com>"]
        assert kwargs["json"]["ConsentToTrack"] == "Unchanged"
        assert kwargs["json"]["Group"] == "Account Verification"
        assert "4321" in kwargs["json"]["Html"]
        assert "4321" in kwargs["json"]["Text"]
        assert "expires in 15 minutes" in kwargs["json"]["Text"]


def test_verification_templates_render_name_and_code() -> None:
    from app.email_templates import render_email_template

    html = render_email_template(
        "verification.html",
        to_name="Ada",
        code="2468",
        expire_minutes=10,
    )
    text = render_email_template(
        "verification.txt",
        to_name="Ada",
        code="2468",
        expire_minutes=10,
    )
    assert "Ada" in html and "2468" in html and "10 minutes" in html
    assert "Ada" in text and "2468" in text and "10 minutes" in text


def test_send_includes_client_id_when_configured() -> None:
    settings = Settings(
        campaign_monitor_api_key="cm-test-key",
        campaign_monitor_sender_email="noreply@example.com",
        campaign_monitor_client_id="client-123",
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "[]"

    with patch("app.services.email_service.httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = mock_response
        EmailService(settings).send_verification_email(
            to_email="user@example.com",
            to_name="User",
            code="1111",
        )
        _, kwargs = client.post.call_args
        assert kwargs["params"] == {"clientID": "client-123"}


def test_send_raises_on_campaign_monitor_error_status() -> None:
    settings = Settings(
        campaign_monitor_api_key="cm-test-key",
        campaign_monitor_sender_email="noreply@example.com",
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
        campaign_monitor_api_key="cm-test-key",
        campaign_monitor_sender_email="noreply@example.com",
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
