from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from .config import load_config
from .database import init_db
from .dialogs import list_dialogs
from .exporter import export_all, export_combined
from .google_docs import update_google_doc
from .sync import sync_all


DEFAULT_CONFIG = "config.yaml"


def configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="telegram-context-sync",
        description="Sync selected Telegram chats into structured Markdown context files.",
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Path to config YAML file")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db", help="Create or update the local SQLite schema")
    subparsers.add_parser("sync", help="Sync enabled Telegram chats into SQLite")
    subparsers.add_parser("export", help="Export configured chats from SQLite to Markdown")
    subparsers.add_parser("combined-export", help="Export all configured chats into one Markdown file")
    subparsers.add_parser("upload-google-doc", help="Update the configured Google Doc from the combined Markdown export")
    subparsers.add_parser("run", help="Run sync, then export individual and combined Markdown files")
    subparsers.add_parser("run-and-upload", help="Run sync, export combined Markdown, then update the configured Google Doc")

    list_chats_parser = subparsers.add_parser("list-chats", help="List Telegram chats visible to the logged-in account")
    list_chats_parser.add_argument("--limit", type=int, default=100, help="Maximum number of dialogs to list")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)

    config = load_config(Path(args.config))

    if args.command == "init-db":
        init_db(config.database_path)
        print(f"Initialized database: {config.database_path}")
        return

    if args.command == "sync":
        asyncio.run(sync_all(config))
        return

    if args.command == "export":
        exported = export_all(config)
        for path in exported:
            print(f"Exported: {path}")
        return

    if args.command == "combined-export":
        path = export_combined(config)
        print(f"Exported combined context: {path}")
        return

    if args.command == "upload-google-doc":
        path = export_combined(config)
        document_id = update_google_doc(config, path)
        print(f"Updated Google Doc: {document_id}")
        return

    if args.command == "run":
        asyncio.run(sync_all(config))
        exported = export_all(config)
        for path in exported:
            print(f"Exported: {path}")
        combined_path = export_combined(config)
        print(f"Exported combined context: {combined_path}")
        return

    if args.command == "run-and-upload":
        asyncio.run(sync_all(config))
        path = export_combined(config)
        print(f"Exported combined context: {path}")
        document_id = update_google_doc(config, path)
        print(f"Updated Google Doc: {document_id}")
        return

    if args.command == "list-chats":
        asyncio.run(list_dialogs(config, limit=args.limit))
        return

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
