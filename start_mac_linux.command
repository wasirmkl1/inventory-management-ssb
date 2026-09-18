#!/usr/bin/env bash
# ============================================================
#  Sani Shwapno Bazar - Inventory Launcher (macOS / Linux)
#  Double-click this file (macOS: you may need to right-click ->
#  Open the first time, since it's from the internet).
#  First run: sets up everything automatically (slower, one-time).
#  Later runs: starts instantly.
#
#  If anything goes wrong, this window will stay open and show the
#  error message instead of closing -- read it before closing.
# ============================================================

cd "$(dirname "$0")"

fail() {
    echo
    echo "[ERROR] $1"
    echo
    read -p "Press Enter to close..." _
    exit 1
}

if ! command -v python3 >/dev/null 2>&1; then
    fail "Python was not found on this computer. Install it from https://www.python.org/downloads/ then double-click this file again."
fi

# If a previous run partially failed, the venv folder may exist but be
# broken (missing python inside it). Treat that the same as "missing".
if [ -d venv ] && [ ! -x venv/bin/python ]; then
    echo "Found a leftover, incomplete 'venv' folder from a previous attempt -- removing it and starting the one-time setup again."
    rm -rf venv
fi

if [ ! -d venv ]; then
    echo "First time setup - this may take a minute, please wait..."
    echo

    echo "Creating the virtual environment..."
    python3 -m venv venv || fail "Failed to create the virtual environment. See the message above for details."

    echo "Installing dependencies (needs an internet connection)..."
    venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt \
        || fail "Installing dependencies failed. This usually means there was no internet connection during setup. Check your connection and double-click this file again -- it will retry the failed steps."

    echo "Setting up the database..."
    venv/bin/python manage.py migrate || fail "Database setup failed. See the message above."

    echo
    echo "Setup complete. If this is a brand new database, create an admin"
    echo "login now (you'll be asked for a username and password):"
    venv/bin/python manage.py createsuperuser
else
    venv/bin/python manage.py migrate || fail "Database setup failed. See the message above."
fi

echo
echo "Starting the server... KEEP THIS WINDOW OPEN while you use the app."
echo "To stop the app later: come back to this window and press Ctrl+C."
echo

# Open the browser shortly after the server starts.
( sleep 2
  if command -v open >/dev/null 2>&1; then
      open "http://127.0.0.1:8000/"        # macOS
  elif command -v xdg-open >/dev/null 2>&1; then
      xdg-open "http://127.0.0.1:8000/"    # Linux
  fi
) &

venv/bin/python manage.py runserver 127.0.0.1:8000
status=$?
if [ $status -ne 0 ]; then
    fail "The server exited with an error (see above). Common causes: another program is already using port 8000, or the database needs attention."
fi
