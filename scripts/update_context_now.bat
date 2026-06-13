@echo off
setlocal

title Telegram Context Sync - Manual Update

REM Run from the repo root no matter where this file is launched from.
cd /d "%~dp0\.."

REM Make src package importable even if editable install has not been run yet.
set PYTHONPATH=%CD%\src

if not exist logs mkdir logs

if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

echo ========================================
echo Telegram Context Sync - Manual Update
echo Repo: %CD%
echo Started: %DATE% %TIME%
echo ========================================
echo.

%PYTHON% -m telegram_context_sync.cli --config config.yaml run-and-upload
set EXIT_CODE=%ERRORLEVEL%

echo.
echo ========================================
echo Finished: %DATE% %TIME%
echo Exit code: %EXIT_CODE%
echo ========================================

echo [%DATE% %TIME%] Manual update finished with exit code %EXIT_CODE% >> logs\manual_update.log

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Update failed. Check the output above and logs\manual_update.log.
) else (
    echo.
    echo Update completed successfully.
)

echo.
pause
endlocal
