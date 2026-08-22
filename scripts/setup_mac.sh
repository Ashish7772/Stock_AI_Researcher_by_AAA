#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install Python 3.11–3.13, then run this script again."
  exit 1
fi

PYVER=$(python3 - <<'PY2'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY2
)
echo "Using Python $PYVER"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
bash scripts/verify_mac.sh

echo
echo "Setup complete. Run: bash scripts/run_mac.sh"
