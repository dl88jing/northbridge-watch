#!/usr/bin/env python3
"""One-shot offline demo for judges — prints perception → decision → action."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from northbridge_watch.agent.orchestrator import AgentOrchestrator
from northbridge_watch.agent.policy import PolicyEngine
from northbridge_watch.vision.detector import AnomalyDetector
from northbridge_watch.vision.scenes import list_scene_kinds, write_scene_fixtures

DEMO_NOW = datetime(2026, 9, 15, 15, 0, 0, tzinfo=timezone.utc)


class DaytimePolicy(PolicyEngine):
    def decide(self, detection_dict, now=None):
        return super().decide(detection_dict, now=DEMO_NOW)


def main() -> None:
    import cv2

    scenes = ROOT / "fixtures" / "scenes"
    write_scene_fixtures(scenes)
    orch = AgentOrchestrator(
        detector=AnomalyDetector(),
        policy=DaytimePolicy(),
        artifact_dir=ROOT / "fixtures" / "annotated",
    )
    print(f"Northbridge Watch | OpenCV {cv2.__version__}")
    print("=" * 60)
    for kind in list_scene_kinds():
        trace = orch.run_on_image(scenes / f"{kind.value}.jpg")
        primary = trace.perception.get("primary")
        print(f"\nScene: {kind.value}")
        print(
            f"  Perception: {primary['label'] if primary else 'none'} "
            f"(conf={primary['confidence'] if primary else 0}) "
            f"n={len(trace.perception.get('detections') or [])}"
        )
        print(f"  Decision:   {trace.decision['action']} — {trace.decision['reason']}")
        print(f"  Brief:      {trace.decision['speakable_brief']}")
        print(f"  Actions:    {json.dumps(trace.actions_taken)}")
    print("\nOK — agentic loop complete. See fixtures/annotated/ and fixtures/events/")


if __name__ == "__main__":
    main()
