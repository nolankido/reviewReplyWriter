@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 rrw_web.py
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python 3.10 or newer is required. Install Python, then run this launcher again.
        pause
        exit /b 1
    )
    python rrw_web.py
)
if errorlevel 1 pause
