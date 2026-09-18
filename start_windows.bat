@echo off
REM ============================================================
REM  Sani Shwapno Bazar - Inventory Launcher (Windows)
REM  Double-click this file. No typing commands required.
REM  First run: sets up everything automatically (slower, one-time).
REM  Later runs: starts instantly.
REM
REM  If anything goes wrong, this window will stay open and show
REM  the error message instead of closing -- read it before you
REM  close the window.
REM
REM  This script intentionally avoids multi-line "if ... ( ... )" blocks,
REM  since those can trigger a "was unexpected at this time" parser
REM  error in cmd.exe. Everything below uses simple, single-line checks
REM  with goto instead.
REM ============================================================

setlocal
cd /d "%~dp0"

echo Checking Python...
where python >nul 2>nul
if errorlevel 1 goto :no_python

python --version >nul 2>nul
if errorlevel 1 goto :no_python
goto :python_ok

:no_python
echo.
echo  [ERROR] Python was not found, or the "python" command on this
echo  computer does not actually work (this happens with the Windows
echo  Store's Python placeholder).
echo  Install real Python from https://www.python.org/downloads/
echo  During install, check "Add python.exe to PATH".
echo  Then double-click this file again.
echo.
pause
exit /b 1

:python_ok
REM If a previous run partially failed, the venv folder may exist but be
REM broken (missing python.exe inside it). Treat that the same as "missing".
if not exist venv\Scripts\python.exe goto :maybe_clean_venv
goto :venv_exists

:maybe_clean_venv
if not exist venv goto :first_time_setup
echo.
echo  Found a leftover, incomplete "venv" folder from a previous
echo  attempt -- removing it and starting the one-time setup again.
echo.
rmdir /s /q venv
goto :first_time_setup

:first_time_setup
echo First time setup - this may take a minute, please wait...
echo.

echo Creating the virtual environment...
python -m venv venv
if errorlevel 1 goto :setup_failed

echo Installing dependencies (needs an internet connection)...
set REQ_FILE=requirements.txt
venv\Scripts\python.exe -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,8) else 1)"
if not errorlevel 1 set REQ_FILE=requirements-win7.txt
if "%REQ_FILE%"=="requirements-win7.txt" echo Detected Python 3.8 (e.g. Windows 7) - using requirements-win7.txt instead.
venv\Scripts\python.exe -m pip install --disable-pip-version-check -r %REQ_FILE%
if errorlevel 1 goto :pip_failed

echo Setting up the database...
venv\Scripts\python.exe manage.py migrate
if errorlevel 1 goto :setup_failed

echo.
echo Setup complete. If this is a brand new database, create an admin
echo login now (you'll be asked for a username and password):
venv\Scripts\python.exe manage.py createsuperuser
goto :start_server

:venv_exists
venv\Scripts\python.exe manage.py migrate
if errorlevel 1 goto :setup_failed
goto :start_server

:setup_failed
echo.
echo  [ERROR] Setup failed. See the message above for details.
echo.
pause
exit /b 1

:pip_failed
echo.
echo  [ERROR] Installing dependencies failed. This usually means
echo  there was no internet connection during setup.
echo  Check your connection and double-click this file again --
echo  it will retry the failed steps, it won't redo finished ones.
echo.
pause
exit /b 1

:start_server
echo.
echo Starting the server in a new window - KEEP THAT WINDOW OPEN while you use the app.
start "SSB Inventory Server - keep this window open" cmd /k venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000

timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:8000/

echo.
echo The app should now be open in your browser at http://127.0.0.1:8000/
echo If not, open that address manually -- and check the other
echo "Server" window for any error messages.
echo To stop the app later: close the other "Server" window (or press Ctrl+C in it).
echo.
pause
