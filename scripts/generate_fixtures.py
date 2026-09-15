#!/usr/bin/env python3
"""Generate demo scene images + run agent loop → annotated + demo JSON for Vercel."""

from __future__ import annotations

import base64
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from northbridge_watch.agent.orchestrator import AgentOrchestrator
from northbridge_watch.agent.policy import PolicyEngine
from northbridge_watch.vision.detector import AnomalyDetector
from northbridge_watch.vision.scenes import SCENE_SPECS, list_scene_kinds, write_scene_fixtures

# Fixed daytime so quiet-hours do not hide notify/human paths for judges
DEMO_NOW = datetime(2026, 9, 15, 15, 0, 0, tzinfo=timezone.utc)


class DaytimePolicy(PolicyEngine):
    def decide(self, detection_dict, now=None):
        return super().decide(detection_dict, now=DEMO_NOW)


def main() -> None:
    scenes_dir = ROOT / "fixtures" / "scenes"
    annotated_dir = ROOT / "fixtures" / "annotated"
    demo_dir = ROOT / "web" / "public" / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)

    paths = write_scene_fixtures(scenes_dir)
    print(f"Wrote {len(paths)} scenes → {scenes_dir}")

    orch = AgentOrchestrator(
        detector=AnomalyDetector(),
        policy=DaytimePolicy(),
        artifact_dir=annotated_dir,
    )
    catalog = []
    for kind in list_scene_kinds():
        path = scenes_dir / f"{kind.value}.jpg"
        # Bypass quiet hours via DaytimePolicy on orchestrator — but orchestrator calls policy.decide without now
        # so DaytimePolicy overrides now.
        trace = orch.run_on_image(path, source="fixture")
        spec = SCENE_SPECS[kind]
        ann = Path(trace.annotated_path) if trace.annotated_path else None
        shutil.copy2(path, demo_dir / f"{kind.value}.jpg")
        ann_name = None
        if ann and ann.exists():
            ann_name = f"{kind.value}_annotated.jpg"
            shutil.copy2(ann, demo_dir / ann_name)
        entry = {
            "id": kind.value,
            "title": spec.title,
            "description": spec.description,
            "expected_label": spec.expected_label,
            "image": f"/demo/{kind.value}.jpg",
            "annotated": f"/demo/{ann_name}" if ann_name else None,
            "trace": trace.to_dict(),
        }
        catalog.append(entry)
        primary = trace.perception.get("primary")
        print(
            f"  {kind.value}: action={trace.decision['action']} "
            f"primary={primary['label'] if primary else None} "
            f"n={len(trace.perception.get('detections') or [])}"
        )

    (demo_dir / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    (ROOT / "fixtures" / "demo_catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(f"Demo catalog → {demo_dir / 'catalog.json'}")


if __name__ == "__main__":
    main()
