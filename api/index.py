"""Vercel Python serverless entry: the real OpenCV 5 + policy pipeline behind /api/*."""

import os
import sys
from pathlib import Path

os.environ.setdefault("NW_FIXTURE_DIR", "/tmp/nw/scenes")
os.environ.setdefault("NW_ARTIFACT_DIR", "/tmp/nw/annotated")
os.environ.setdefault("NW_EVENT_DIR", "/tmp/nw/events")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from northbridge_watch.api.server import app  # noqa: E402,F401
