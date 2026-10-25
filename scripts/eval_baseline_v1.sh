#!/usr/bin/env bash
# Re-run the evaluation against the original (v1, commit 2fe7893) detector for the before/after table.
set -euo pipefail
cd "$(dirname "$0")/.."
git show 2fe7893:northbridge_watch/vision/detector.py > /tmp/detector_v1.py
python - <<'PY'
import importlib.util, runpy, sys
spec = importlib.util.spec_from_file_location("northbridge_watch.vision.detector", "/tmp/detector_v1.py")
m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
sys.argv = ["run_eval", "--n", "40", "--seed0", "50000", "--out", "docs/eval/baseline-v1"]
runpy.run_module("northbridge_watch.eval.run_eval", run_name="__main__")
PY
