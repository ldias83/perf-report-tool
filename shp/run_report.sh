#!/bin/bash

# --------------------------
# Configuration
# --------------------------
CONFIG_FILE="config/chronocache.json"
VERSION="$1"
VENV_DIR=".venv"

# --------------------------
# Argument Check
# --------------------------
if [ -z "$VERSION" ]; then
  echo "Usage: ./run_report.sh <version>"
  exit 1
fi

# --------------------------
# Create Virtual Environment if needed
# --------------------------
if [ ! -d "$VENV_DIR" ]; then
  echo "[*] Creating virtual environment..."
  python3 -m venv $VENV_DIR
fi

# --------------------------
# Activate Virtual Environment
# --------------------------
source $VENV_DIR/bin/activate

# --------------------------
# Install Python Dependencies
# --------------------------
echo "[*] Installing required packages..."
pip install --quiet --upgrade pip
pip install --quiet pandas plotly jinja2

# --------------------------
# Run the Report Generator
# --------------------------
echo "[*] Generating performance report for version: $VERSION"
python generate_report.py $CONFIG_FILE $VERSION

# --------------------------
# Deactivate Virtual Environment
# --------------------------
deactivate

echo "[✓] Done."
