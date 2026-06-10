from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
from typing import Any

from dotenv import load_dotenv
import yaml


@dataclass(frozen=True)
class ChatConfig:
    name: str
    identifier: str | int
    enabled: bool = True
    export_file: str | None = None


@dataclass(frozen=True)
class TelegramConfig:
    api_id: int
    api_hash: str
    phone: str | None
    session_name: str = "telegram_context_sync"
    request_limit: int = 1000


@dataclass(frozen=True)
class MarkdownConfig:
    max_messages_per_file: int = 500
    include_sender: bool = True
    include_source_identifier: bool = True


@dataclass(frozen=True)
class GoogleConfig:
    enabled: bool = False
    credentials_path: Path = Path("credentials/client_secret.json")
    token_path: Path = Path("token.json")
    document_id: str | None = None
    document_title: str = "Telegram Context Sync - Project Context"


@dataclass(frozen=True)
class AppConfig:
    timezone: str = "America/New_York"
    database_path: Path = Path("data/context.db")
    export_dir: Path = Path("exports")
    combined_export_file: str = "project_context.md"
    telegram: TelegramConfig | None = None
    markdown: MarkdownConfig = field(default_factory=MarkdownConfig)
    google: GoogleConfig = field(default_factory=GoogleConfig)
    chats: list[ChatConfig] = field(default_factory=list)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _normalize_identifier(value: str | int) -> str | int:
    """Convert quoted numeric Telegram peer IDs from YAML into integers."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
        return stripped
    return value


def load_config(config_path: str | Path) -> AppConfig:
    """Load YAML config and Telegram credentials from environment variables."""
    load_dotenv()

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    telegram_raw = raw.get("telegram", {}) or {}
    markdown_raw = raw.get("markdown", {}) or {}
    google_raw = raw.get("google", {}) or {}

    session_name = os.getenv("TELEGRAM_SESSION_NAME") or telegram_raw.get("session_name") or "telegram_context_sync"

    telegram = TelegramConfig(
        api_id=int(_require_env("TELEGRAM_API_ID")),
        api_hash=_require_env("TELEGRAM_API_HASH"),
        phone=os.getenv("TELEGRAM_PHONE"),
        session_name=session_name,
        request_limit=int(telegram_raw.get("request_limit", 1000)),
    )

    google = GoogleConfig(
        enabled=bool(google_raw.get("enabled", False)),
        credentials_path=Path(google_raw.get("credentials_path", "credentials/client_secret.json")),
        token_path=Path(google_raw.get("token_path", "token.json")),
        document_id=str(google_raw.get("document_id") or "").strip() or None,
        document_title=str(google_raw.get("document_title", "Telegram Context Sync - Project Context")),
    )

    chats = [
        ChatConfig(
            name=str(item["name"]),
            identifier=_normalize_identifier(item["identifier"]),
            enabled=bool(item.get("enabled", True)),
            export_file=item.get("export_file"),
        )
        for item in raw.get("chats", [])
    ]

    return AppConfig(
        timezone=str(raw.get("timezone", "America/New_York")),
        database_path=Path(raw.get("database_path", "data/context.db")),
        export_dir=Path(raw.get("export_dir", "exports")),
        combined_export_file=str(raw.get("combined_export_file", "project_context.md")),
        telegram=telegram,
        markdown=MarkdownConfig(
            max_messages_per_file=int(markdown_raw.get("max_messages_per_file", 500)),
            include_sender=bool(markdown_raw.get("include_sender", True)),
            include_source_identifier=bool(markdown_raw.get("include_source_identifier", True)),
        ),
        google=google,
        chats=chats,
    )
