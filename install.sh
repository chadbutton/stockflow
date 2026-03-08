#!/usr/bin/env bash
# Install project (unr_setup + backend). Run from repo root: ./install.sh
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if ! command -v python3 &>/dev/null; then
  if ! command -v python &>/dev/null; then
    echo "Python not found. Install from https://www.python.org/downloads/"
    exit 1
  fi
  PY=python
else
  PY=python3
fi

echo "Using: $PY"
"$PY" -m pip install --upgrade pip -q
echo "Installing unr_setup..."
"$PY" -m pip install -e "$ROOT/unr_setup"
echo "Installing backend..."
"$PY" -m pip install -e "$ROOT/backend"
echo "Done. Run Friday scan: cd backend && $PY -m scanner.cli --yahoo --as-of 2025-03-07 -o watchlist.json"
