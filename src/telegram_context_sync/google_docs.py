from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .config import AppConfig
from .exporter import export_combined


SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]


def _load_credentials(config: AppConfig) -> Credentials:
    token_path = config.google.token_path
    credentials_path = config.google.credentials_path

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not credentials_path.exists():
            raise FileNotFoundError(
                f"Google OAuth client secret not found: {credentials_path}. "
                "Create a desktop OAuth client in Google Cloud and place the downloaded JSON there."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True) if token_path.parent != Path(".") else None
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def update_google_doc(config: AppConfig, markdown_path: Path | None = None) -> str:
    if not config.google.enabled:
        raise RuntimeError("Google integration is disabled. Set google.enabled: true in config.yaml.")

    if markdown_path is None:
        markdown_path = export_combined(config)

    markdown_text = markdown_path.read_text(encoding="utf-8")
    creds = _load_credentials(config)

    docs_service = build("docs", "v1", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)

    document_id = config.google.document_id
    if not document_id:
        document = docs_service.documents().create(body={"title": config.google.document_title}).execute()
        document_id = document["documentId"]
        print(f"Created Google Doc: {document_id}")
        print("Add this document_id to config.yaml under google.document_id so future runs update the same doc.")

    document = docs_service.documents().get(documentId=document_id).execute()
    body_content = document.get("body", {}).get("content", [])
    end_index = body_content[-1].get("endIndex", 1) if body_content else 1

    requests: list[dict] = []
    if end_index > 2:
        requests.append({"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end_index - 1}}})

    requests.append({"insertText": {"location": {"index": 1}, "text": markdown_text}})

    docs_service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()

    drive_service.permissions().create(
        fileId=document_id,
        body={"type": "user", "role": "writer", "emailAddress": ""},
        fields="id",
    ) if False else None

    return document_id
