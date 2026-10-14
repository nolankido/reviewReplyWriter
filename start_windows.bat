@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 goto use_py
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 goto use_python
echo Python 3.10 or newer is required. Install Python, then run this launcher again.
pause
exit /b 1

:use_py
py -3 rrw_setup.py --launch %*
set "RRW_EXIT=%errorlevel%"
goto finish

:use_python
python rrw_setup.py --launch %*
set "RRW_EXIT=%errorlevel%"

:finish
if not "%RRW_EXIT%"=="0" pause
exit /b %RRW_EXIT%
