#!/usr/bin/env bash
# Rebuild docs/pitch-deck.pdf from docs/deck/pitch-deck.html with headless Chrome.
set -euo pipefail
cd "$(dirname "$0")/.."
CHROME="${CHROME:-google-chrome}"
"$CHROME" --headless --no-sandbox --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$PWD/docs/pitch-deck.pdf" "file://$PWD/docs/deck/pitch-deck.html"
echo "wrote docs/pitch-deck.pdf"
