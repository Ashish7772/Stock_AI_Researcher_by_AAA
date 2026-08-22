#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -d ".venv" ]; then
  echo "Virtual environment not found. Run: bash scripts/setup_mac.sh"
  exit 1
fi
source .venv/bin/activate
python -m streamlit run app/main.py
