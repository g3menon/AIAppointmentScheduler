"""Build Google credentials from environment (OAuth refresh or service account).

Service-account mode supports, in order:
1. ``GOOGLE_SERVICE_ACCOUNT_JSON`` — inline JSON (e.g. secret injected at runtime; not a file path).
2. ``GOOGLE_SERVICE_ACCOUNT_FILE`` — explicit path to a key JSON file (local dev default).
3. ``GOOGLE_APPLICATION_CREDENTIALS`` — standard ADC file path used by Google client libraries.
4. `Application Default Credentials`_ (metadata server, ``gcloud auth application-default login``, etc.).

.. _Application Default Credentials: https://cloud.google.com/docs/authentication/application-default-credentials
"""

from __future__ import annotations

import json
import os

import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.compose",
]


def _apply_delegated_subject(creds: Credentials, subject: str) -> Credentials:
    if not subject:
        return creds
    if isinstance(creds, service_account.Credentials):
        return creds.with_subject(subject)
    raise ValueError(
        "GOOGLE_DELEGATED_SUBJECT only applies to service account credentials; "
        "use a service account JSON file, inline JSON, or ADC that resolves to a service account."
    )


def _load_service_account_credentials() -> Credentials:
    subject = os.environ.get("GOOGLE_DELEGATED_SUBJECT", "").strip()

    json_blob = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if json_blob:
        info = json.loads(json_blob)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        return _apply_delegated_subject(creds, subject)

    path = (
        os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
        or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    )
    if path:
        creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
        return _apply_delegated_subject(creds, subject)

    creds, _project_id = google.auth.default(scopes=SCOPES)
    return _apply_delegated_subject(creds, subject)


def load_credentials() -> Credentials:
    mode = os.environ.get("GOOGLE_AUTH_MODE", "service_account").strip().lower()
    if mode == "service_account":
        try:
            return _load_service_account_credentials()
        except Exception as exc:
            raise ValueError(
                "Service account auth failed. Set one of: GOOGLE_SERVICE_ACCOUNT_FILE (path to JSON), "
                "GOOGLE_APPLICATION_CREDENTIALS (ADC file path), GOOGLE_SERVICE_ACCOUNT_JSON (inline JSON), "
                "or configure Application Default Credentials. Original error: "
                f"{exc}"
            ) from exc

    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    refresh = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "").strip()
    if not (client_id and client_secret and refresh):
        raise ValueError(
            "OAuth requires GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, and GOOGLE_OAUTH_REFRESH_TOKEN"
        )
    creds = Credentials(
        token=None,
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds
