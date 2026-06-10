from __future__ import annotations

from datetime import datetime, timezone
import logging
from zoneinfo import ZoneInfo

from telethon import TelegramClient

from .config import AppConfig, ChatConfig
from .database import connect, get_last_message_id, init_db, insert_messages, update_last_message_id, upsert_chat

logger = logging.getLogger(__name__)


def _sender_name(sender: object | None) -> tuple[str | None, str | None]:
    if sender is None:
        return None, None

    sender_id = str(getattr(sender, "id", "")) or None

    title = getattr(sender, "title", None)
    username = getattr(sender, "username", None)
    first_name = getattr(sender, "first_name", None)
    last_name = getattr(sender, "last_name", None)

    if title:
        return sender_id, str(title)
    if username:
        return sender_id, f"@{username}"

    full_name = " ".join(part for part in [first_name, last_name] if part)
    return sender_id, full_name or sender_id


async def sync_all(config: AppConfig) -> None:
    if config.telegram is None:
        raise RuntimeError("Telegram config is missing")

    init_db(config.database_path)
    local_tz = ZoneInfo(config.timezone)

    client = TelegramClient(
        config.telegram.session_name,
        config.telegram.api_id,
        config.telegram.api_hash,
    )

    await client.start(phone=config.telegram.phone)

    try:
        for chat in config.chats:
            if not chat.enabled:
                logger.info("Skipping disabled chat: %s", chat.name)
                continue
            await sync_chat(client, config, chat, local_tz)
    finally:
        await client.disconnect()


async def sync_chat(client: TelegramClient, config: AppConfig, chat: ChatConfig, local_tz: ZoneInfo) -> None:
    logger.info("Syncing chat: %s", chat.name)

    now_local = datetime.now(timezone.utc).astimezone(local_tz).isoformat(timespec="seconds")

    with connect(config.database_path) as conn:
        upsert_chat(
            conn,
            name=chat.name,
            identifier=str(chat.identifier),
            export_file=chat.export_file,
            updated_at=now_local,
        )
        last_message_id = get_last_message_id(conn, chat.name)

    entity = await client.get_entity(chat.identifier)
    rows: list[dict] = []
    highest_message_id = last_message_id

    async for message in client.iter_messages(
        entity,
        min_id=last_message_id,
        reverse=True,
        limit=config.telegram.request_limit,
    ):
        text = (message.message or "").strip()
        if not text:
            continue

        sender = await message.get_sender()
        sender_id, sender_display = _sender_name(sender)

        message_date = message.date.astimezone(local_tz).isoformat(timespec="seconds")
        highest_message_id = max(highest_message_id, int(message.id))

        rows.append(
            {
                "chat_name": chat.name,
                "chat_identifier": str(chat.identifier),
                "message_id": int(message.id),
                "message_date": message_date,
                "sender_id": sender_id,
                "sender_name": sender_display,
                "text": text,
                "synced_at": now_local,
            }
        )

    with connect(config.database_path) as conn:
        inserted_or_changed = insert_messages(conn, rows)
        update_last_message_id(conn, chat.name, highest_message_id, now_local)

    logger.info(
        "Finished chat %s: fetched=%s, database_changes=%s, last_message_id=%s",
        chat.name,
        len(rows),
        inserted_or_changed,
        highest_message_id,
    )
