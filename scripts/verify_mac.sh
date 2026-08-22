#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
python -m py_compile app/*.py tests/*.py
PYTHONPATH=. python -m pytest -q tests/test_core.py tests/test_end_to_end_mock.py
echo
echo "✅ Verified: core + full analysis-path tests passed."
