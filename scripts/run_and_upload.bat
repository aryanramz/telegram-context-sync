@echo off
setlocal

REM Run from the repo root no matter where Task Scheduler starts.
cd /d "%~dp0\.."

REM Make src package importable even if editable install has not been run yet.
set PYTHONPATH=%CD%\src

if not exist logs mkdir logs

if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

%PYTHON% -m telegram_context_sync.cli --config config.yaml run-and-upload >> logs\run_and_upload.log 2>&1

endlocal
