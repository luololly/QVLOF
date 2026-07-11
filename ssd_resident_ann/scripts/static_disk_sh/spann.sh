#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

python "${ROOT_DIR}/qso/static_layout_main.py" \
  --system spann \
  --train-queries "$1" \
  --vector-features "$2" \
  --num-vectors "$3" \
  --page-capacity "$4" \
  --posting-membership "$5" \
  --output-dir "$6" \
  --prefix "$7" \
  "${@:8}"
