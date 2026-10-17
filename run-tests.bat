@echo off
rem Runs every test plus a hardware check and writes it all to test-results.txt.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PY=python
if exist .venv\Scripts\python.exe set PY=.venv\Scripts\python.exe
set OUT=test-results.txt

echo Power Meter test run %date% %time% > %OUT%
echo.>> %OUT%
echo === install dev tools ===>> %OUT%
%PY% -m pip install -q -e ".[dev]" >> %OUT% 2>&1
echo.>> %OUT%
echo === pytest ===>> %OUT%
%PY% -m pytest -q >> %OUT% 2>&1
echo.>> %OUT%
echo === ruff ===>> %OUT%
%PY% -m ruff check . >> %OUT% 2>&1
echo.>> %OUT%
echo === game engine tests ===>> %OUT%
where node >nul 2>&1
if errorlevel 1 (
    echo Node.js is not installed, skipped>> %OUT%
) else (
    node --test tests/js/engine.test.js >> %OUT% 2>&1
)
echo.>> %OUT%
echo === hardware check ===>> %OUT%
%PY% -m power_meter check >> %OUT% 2>&1
echo.>> %OUT%
echo === done ===>> %OUT%
