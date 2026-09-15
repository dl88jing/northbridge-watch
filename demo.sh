#!/usr/bin/env bash
# Northbridge Watch — judge quickstart
set -euo pipefail
cd "$(dirname "$0")"

CMD="${1:-demo}"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -U pip
  .venv/bin/pip install -q -r requirements.txt
  .venv/bin/pip install -q -e .
fi
# shellcheck disable=SC1091
source .venv/bin/activate

case "$CMD" in
  demo)
    python scripts/generate_fixtures.py
    python scripts/run_demo.py
    ;;
  fixtures)
    python scripts/generate_fixtures.py
    ;;
  serve|api)
    python scripts/generate_fixtures.py
    exec python -m northbridge_watch.api.server
    ;;
  web)
    cd web
    if [[ ! -d node_modules ]]; then npm install; fi
    exec npm run dev
    ;;
  all)
    python scripts/generate_fixtures.py
    python -m northbridge_watch.api.server &
    API_PID=$!
    trap 'kill $API_PID 2>/dev/null || true' EXIT
    cd web
    if [[ ! -d node_modules ]]; then npm install; fi
    npm run dev
    ;;
  *)
    echo "Usage: ./demo.sh [demo|fixtures|serve|web|all]"
    exit 1
    ;;
esac
