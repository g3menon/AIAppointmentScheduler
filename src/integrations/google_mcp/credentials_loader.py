"""Build Google credentials from environment (OAuth refresh or service account)."""

from __future__ import annotations

import os

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.compose",
]


def load_credentials() -> Credentials:
    mode = os.environ.get("GOOGLE_AUTH_MODE", "service_account").strip().lower()
    if mode == "service_account":
        path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
        if not path:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_FILE is required when GOOGLE_AUTH_MODE=service_account")
        creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
        subject = os.environ.get("GOOGLE_DELEGATED_SUBJECT", "").strip()
        if subject:
            # Required for Gmail API as userId='me' (Workspace: enable domain-wide delegation + authorize scopes).
            creds = creds.with_subject(subject)
        return creds

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
