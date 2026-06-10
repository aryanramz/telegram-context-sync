from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from .config import AppConfig, ChatConfig
from .database import connect, fetch_recent_messages


SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def safe_filename(value: str) -> str:
    cleaned = SAFE_FILENAME_RE.sub("_", value.strip()).strip("_")
    return cleaned or "chat"


def export_all(config: AppConfig) -> list[Path]:
    config.export_dir.mkdir(parents=True, exist_ok=True)
    exported: list[Path] = []

    for chat in config.chats:
        if not chat.enabled:
            continue
        exported.append(export_chat(config, chat))

    return exported


def export_chat(config: AppConfig, chat: ChatConfig) -> Path:
    output_name = chat.export_file or f"{safe_filename(chat.name)}.md"
    output_path = config.export_dir / output_name

    with connect(config.database_path) as conn:
        rows = fetch_recent_messages(conn, chat.name, config.markdown.max_messages_per_file)

    local_tz = ZoneInfo(config.timezone)
    generated_at = datetime.now(timezone.utc).astimezone(local_tz).isoformat(timespec="seconds")

    lines = render_chat_markdown(config, chat, rows, generated_at, heading_level=1)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def export_combined(config: AppConfig) -> Path:
    config.export_dir.mkdir(parents=True, exist_ok=True)
    output_path = config.export_dir / config.combined_export_file

    local_tz = ZoneInfo(config.timezone)
    generated_at = datetime.now(timezone.utc).astimezone(local_tz).isoformat(timespec="seconds")

    enabled_chats = [chat for chat in config.chats if chat.enabled]

    lines: list[str] = []
    lines.append("# Telegram Project Context")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
    lines.append(f"Timezone: {config.timezone}")
    lines.append(f"Configured chats: {len(enabled_chats)}")
    lines.append("")
    lines.append("> This document is generated from selected Telegram chats. Treat it as private operational context.")
    lines.append("")
    lines.append("## Chat index")
    lines.append("")

    chat_payloads: list[tuple[ChatConfig, list]] = []
    with connect(config.database_path) as conn:
        for chat in enabled_chats:
            rows = fetch_recent_messages(conn, chat.name, config.markdown.max_messages_per_file)
            chat_payloads.append((chat, rows))
            latest = rows[-1]["message_date"] if rows else "No messages"
            lines.append(f"- `{chat.name}` — {len(rows)} messages — latest: {latest}")

    lines.append("")
    lines.append("---")
    lines.append("")

    for chat, rows in chat_payloads:
        lines.extend(render_chat_markdown(config, chat, rows, generated_at, heading_level=2, include_file_header=False))
        lines.append("")
        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def render_chat_markdown(
    config: AppConfig,
    chat: ChatConfig,
    rows: list,
    generated_at: str,
    *,
    heading_level: int = 1,
    include_file_header: bool = True,
) -> list[str]:
    grouped: dict[str, list] = defaultdict(list)
    for row in rows:
        day = row["message_date"][:10]
        grouped[day].append(row)

    h = "#" * heading_level
    day_h = "#" * (heading_level + 1)
    message_h = "#" * (heading_level + 2)

    lines: list[str] = []
    if include_file_header:
        lines.append(f"{h} Telegram Context: {chat.name}")
    else:
        lines.append(f"{h} {chat.name}")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
    lines.append(f"Timezone: {config.timezone}")
    if config.markdown.include_source_identifier:
        lines.append(f"Source identifier: `{chat.identifier}`")
    lines.append(f"Message count: {len(rows)}")
    lines.append("")

    if include_file_header:
        lines.append("> This file is generated from a selected Telegram chat. Review before sharing outside your local workflow.")
        lines.append("")

    if not rows:
        lines.append("No synced messages found for this chat yet.")
    else:
        for day, day_rows in grouped.items():
            lines.append(f"{day_h} {day}")
            lines.append("")
            for row in day_rows:
                timestamp = row["message_date"][11:16]
                sender = row["sender_name"] or "Unknown sender"
                text = str(row["text"]).strip()

                if config.markdown.include_sender:
                    lines.append(f"{message_h} {timestamp} — {sender}")
                else:
                    lines.append(f"{message_h} {timestamp}")
                lines.append("")
                lines.append(text)
                lines.append("")

    return lines
