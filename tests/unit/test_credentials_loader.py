"""Service-account credential resolution order (not filesystem-only)."""

from __future__ import annotations

import json
from unittest import mock

import pytest

from src.integrations.google_mcp.credentials_loader import load_credentials


_MINIMAL_SA_INFO = {
    "type": "service_account",
    "project_id": "test-proj",
    "private_key_id": "kid",
    "private_key": (
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7Mhgwkv\n"
        "-----END RSA PRIVATE KEY-----\n"
    ),
    "client_email": "sa@test-proj.iam.gserviceaccount.com",
    "client_id": "123",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
}


def test_service_account_prefers_inline_json_over_file_path(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("GOOGLE_AUTH_MODE", "service_account")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", json.dumps(_MINIMAL_SA_INFO))
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", str(tmp_path / "ignored.json"))

    with mock.patch(
        "src.integrations.google_mcp.credentials_loader.service_account.Credentials.from_service_account_info"
    ) as from_info, mock.patch(
        "src.integrations.google_mcp.credentials_loader.service_account.Credentials.from_service_account_file"
    ) as from_file, mock.patch(
        "src.integrations.google_mcp.credentials_loader.google.auth.default"
    ) as default:
        fake = mock.Mock()
        from_info.return_value = fake
        load_credentials()
        from_info.assert_called_once()
        from_file.assert_not_called()
        default.assert_not_called()


def test_service_account_uses_file_when_no_inline_json(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    p = tmp_path / "key.json"
    p.write_text(json.dumps(_MINIMAL_SA_INFO), encoding="utf-8")
    monkeypatch.setenv("GOOGLE_AUTH_MODE", "service_account")
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", str(p))
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)

    with mock.patch(
        "src.integrations.google_mcp.credentials_loader.service_account.Credentials.from_service_account_info"
    ) as from_info, mock.patch(
        "src.integrations.google_mcp.credentials_loader.service_account.Credentials.from_service_account_file"
    ) as from_file, mock.patch(
        "src.integrations.google_mcp.credentials_loader.google.auth.default"
    ) as default:
        fake = mock.Mock()
        from_file.return_value = fake
        load_credentials()
        from_info.assert_not_called()
        from_file.assert_called_once()
        default.assert_not_called()


def test_service_account_uses_google_application_credentials_when_file_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    p = tmp_path / "adc.json"
    p.write_text(json.dumps(_MINIMAL_SA_INFO), encoding="utf-8")
    monkeypatch.setenv("GOOGLE_AUTH_MODE", "service_account")
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(p))

    with mock.patch(
        "src.integrations.google_mcp.credentials_loader.service_account.Credentials.from_service_account_file"
    ) as from_file, mock.patch(
        "src.integrations.google_mcp.credentials_loader.google.auth.default"
    ) as default:
        fake = mock.Mock()
        from_file.return_value = fake
        load_credentials()
        from_file.assert_called_once_with(str(p), scopes=mock.ANY)
        default.assert_not_called()


def test_service_account_falls_back_to_application_default_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_AUTH_MODE", "service_account")
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_FILE", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)

    with mock.patch(
        "src.integrations.google_mcp.credentials_loader.service_account.Credentials.from_service_account_info"
    ) as from_info, mock.patch(
        "src.integrations.google_mcp.credentials_loader.service_account.Credentials.from_service_account_file"
    ) as from_file, mock.patch(
        "src.integrations.google_mcp.credentials_loader.google.auth.default"
    ) as default:
        fake = mock.Mock()
        default.return_value = (fake, "my-project")
        load_credentials()
        from_info.assert_not_called()
        from_file.assert_not_called()
        default.assert_called_once()
