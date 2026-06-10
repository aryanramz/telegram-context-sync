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

    grouped: dict[str, list] = defaultdict(list)
    for row in rows:
        day = row["message_date"][:10]
        grouped[day].append(row)

    lines: list[str] = []
    lines.append(f"# Telegram Context: {chat.name}")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
    lines.append(f"Timezone: {config.timezone}")
    if config.markdown.include_source_identifier:
        lines.append(f"Source identifier: `{chat.identifier}`")
    lines.append(f"Message count: {len(rows)}")
    lines.append("")
    lines.append("> This file is generated from a selected Telegram chat. Review before sharing outside your local workflow.")
    lines.append("")

    if not rows:
        lines.append("No synced messages found for this chat yet.")
    else:
        for day, day_rows in grouped.items():
            lines.append(f"## {day}")
            lines.append("")
            for row in day_rows:
                timestamp = row["message_date"][11:16]
                sender = row["sender_name"] or "Unknown sender"
                text = str(row["text"]).strip()

                if config.markdown.include_sender:
                    lines.append(f"### {timestamp} — {sender}")
                else:
                    lines.append(f"### {timestamp}")
                lines.append("")
                lines.append(text)
                lines.append("")
                lines.append("---")
                lines.append("")

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path
