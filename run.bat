@echo off
rem Double-click to open the Power Meter app.
cd /d "%~dp0"
set PY=python
if exist .venv\Scripts\python.exe set PY=.venv\Scripts\python.exe

%PY% -c "import webview, power_meter" 2>nul
if errorlevel 1 (
    echo First run: installing what the app needs...
    %PY% -m pip install -q -e .
    if errorlevel 1 (
        echo Install failed. See the error above.
        pause
        exit /b 1
    )
)

start "" "%PY:python.exe=pythonw.exe%" -m power_meter app
