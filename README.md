# telegram-context-sync

A Python utility for syncing selected Telegram chats into structured Markdown context files for personal review and project documentation.

The main goal is to turn selected Telegram conversations into clean, dated Markdown files that can be uploaded into documentation systems or AI project source folders. The repo is intentionally generic and does not assume a specific event, group, or organization.

## Features

- Sync selected Telegram chats using [Telethon](https://docs.telethon.dev/)
- Store synced messages locally in SQLite
- Export structured Markdown files by configured chat
- Track last synced Telegram message ID per chat to avoid duplicate imports
- Keep login/session files local only
- Windows Task Scheduler-compatible batch runner
- Uses `America/New_York` by default

## Security model

This repo is designed so private data stays local.

Do **not** commit:

- `.env`
- `*.session`
- `*.session-journal`
- local SQLite databases
- generated Markdown exports containing private chat content
- raw Telegram chat exports

The `.gitignore` file already blocks those paths. Keep it that way.

## Repo layout

```text
telegram-context-sync/
  README.md
  requirements.txt
  pyproject.toml
  .gitignore
  .env.example
  config.example.yaml
  src/
    telegram_context_sync/
      __init__.py
      config.py
      database.py
      sync.py
      exporter.py
      cli.py
  scripts/
    run_sync.bat
  exports/
    .gitkeep
```

## Setup

### 1. Create a Telegram API app

Go to Telegram's API development page and create an app to get:

- `api_id`
- `api_hash`

Then copy the environment template:

```bash
cp .env.example .env
```

Fill in:

```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+15555555555
TELEGRAM_SESSION_NAME=telegram_context_sync
```

### 2. Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

On macOS/Linux, activate with:

```bash
source .venv/bin/activate
```

### 3. Create local config

```bash
copy config.example.yaml config.yaml
```

Edit `config.yaml` and add only the chats you explicitly want synced.

Example:

```yaml
chats:
  - name: example_project_group
    identifier: "example_public_username_or_chat_id"
    enabled: true
    export_file: "example_project_group.md"
```

For private groups, use a Telegram chat ID or another identifier Telethon can resolve from your logged-in account.

## Usage

Global options must go before the command.

Initialize the database:

```bash
python -m telegram_context_sync.cli --config config.yaml init-db
```

Sync configured chats:

```bash
python -m telegram_context_sync.cli --config config.yaml sync
```

Export Markdown files:

```bash
python -m telegram_context_sync.cli --config config.yaml export
```

Run sync and export together:

```bash
python -m telegram_context_sync.cli --config config.yaml run
```

Generated Markdown files go into `exports/` by default. These are ignored by Git because they may contain private chat content.

## Windows Task Scheduler

Use `scripts/run_sync.bat` as the scheduled task action.

Recommended Task Scheduler settings:

- Trigger: daily, or whatever cadence makes sense
- Action: start a program
- Program/script: full path to `scripts\run_sync.bat`
- Start in: full path to the repo root
- Run whether user is logged on or not, only if the Telegram session is already created and works from that account

Run the script manually first so Telegram login/2FA is completed locally before scheduling it.

## Development notes

- The first run creates a `.session` file for Telethon. That file is local credential material. Do not commit it.
- SQLite stores synced message text locally. Treat the database as private.
- Markdown exports are meant for local review or manual upload into project documentation/source folders. Treat them as private unless you deliberately sanitize them.

## Roadmap

- Add date-range exports
- Add message filtering rules
- Add per-chat summary/front matter options
- Add attachment/media placeholder handling
- Add dry-run mode
- Add log rotation
