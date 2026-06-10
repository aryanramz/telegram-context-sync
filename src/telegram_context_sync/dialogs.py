from __future__ import annotations

from telethon import TelegramClient

from .config import AppConfig


def _format_dialog_type(dialog: object) -> str:
    entity = getattr(dialog, "entity", None)
    if entity is None:
        return "unknown"

    if getattr(entity, "megagroup", False):
        return "supergroup"
    if getattr(entity, "broadcast", False):
        return "channel"

    entity_type = type(entity).__name__.lower()
    if "chat" in entity_type:
        return "group"
    if "user" in entity_type:
        return "user"
    return entity_type


def _telethon_identifier(entity: object) -> str:
    entity_id = getattr(entity, "id", None)
    if entity_id is None:
        return ""

    if getattr(entity, "megagroup", False) or getattr(entity, "broadcast", False):
        return f"-100{entity_id}"

    entity_type = type(entity).__name__.lower()
    if "chat" in entity_type:
        return f"-{entity_id}"

    return str(entity_id)


async def list_dialogs(config: AppConfig, limit: int = 100) -> None:
    if config.telegram is None:
        raise RuntimeError("Telegram config is missing")

    client = TelegramClient(
        config.telegram.session_name,
        config.telegram.api_id,
        config.telegram.api_hash,
    )

    await client.start(phone=config.telegram.phone)

    try:
        print("identifier\ttype\ttitle")
        async for dialog in client.iter_dialogs(limit=limit):
            entity = dialog.entity
            identifier = _telethon_identifier(entity)
            dialog_type = _format_dialog_type(dialog)
            title = dialog.name or getattr(entity, "title", None) or getattr(entity, "username", None) or ""
            print(f"{identifier}\t{dialog_type}\t{title}")
    finally:
        await client.disconnect()
