#!/usr/bin/env bash
# ----------------------------------------------------------------------
# run_report.sh
#   Create / update venv, install deps,
#   then call src/generate_report.py to build an HTML report.
#
# USAGE
#   ./bin/run_report.sh \
#       -t  <dst-root>          # REQUIRED  (e.g. ../ChronoCache)
#       -v  <version-tag>       # REQUIRED  (e.g. v1.0.01)
#      [-n  <folder-name>]      # optional, default = <version-tag>
#      [-c  <cfg-file>]         # optional, default = cfg/default.json
#      [-d  <data-root>]        # optional, default = perf-report-tool root
#
# EXAMPLE
#   ./bin/run_report.sh -t ../ChronoCache -v v1.0.01
# ----------------------------------------------------------------------

set -euo pipefail

# ----------------------------- defaults --------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_ROOT="$SCRIPT_DIR/.."                 # repo root
PY_SCRIPT="$TOOL_ROOT/src/generate_report.py"

CONFIG_FILE="$TOOL_ROOT/cfg/default.json"
DATA_ROOT="$TOOL_ROOT"                     # where gen/{stat,…} lives
DST_ROOT=""
VERSION=""
FOLDER_OVERRIDE=""

# --------------------------- arg parsing --------------------------------
usage() {
  echo "Usage: $0 -t <dst-root> -v <version> [-n <folder>] [-c <cfg>] [-d <data-root>]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--dst)         DST_ROOT="$2"; shift 2 ;;
    -v|--ver)         VERSION="$2"; shift 2 ;;
    -n|--report-name) FOLDER_OVERRIDE="$2"; shift 2 ;;
    -c|--cfg)         CONFIG_FILE="$2"; shift 2 ;;
    -d|--data)        DATA_ROOT="$2"; shift 2 ;;
    *) usage ;;
  esac
done

[[ -n "$DST_ROOT" && -n "$VERSION" ]] || usage
[[ -f "$CONFIG_FILE" ]] || { echo "Config not found: $CONFIG_FILE"; exit 1; }

# default folder name = version tag unless overridden
FOLDER_NAME="${FOLDER_OVERRIDE:-$VERSION}"

# --------------------------- virtualenv ---------------------------------
VENV_DIR="$TOOL_ROOT/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
  echo "[*] Creating virtual environment in $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# minimal deps (quiet install)
pip install -q --upgrade pip
pip install -q pandas plotly jinja2

# ----------------------- generate report -------------------------------
echo "[*] Generating report …"

REPORT_HTML=$(python "$PY_SCRIPT" \
    --config "$CONFIG_FILE" \
    --data   "$DATA_ROOT" \
    --dst    "$DST_ROOT" \
    --ver    "$FOLDER_NAME")

deactivate   # leave the venv

echo "[✓] Done.  HTML saved at: $REPORT_HTML"
