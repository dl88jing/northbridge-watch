"""Perception → decision → action loop with auditable trace."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from northbridge_watch.agent.policy import ActionDecision, ActionKind, PolicyEngine
from northbridge_watch.aws.handler import LocalEventStore, build_event_payload
from northbridge_watch.vision.detector import AnomalyDetector, DetectionResult


@dataclass
class AgentTrace:
    trace_id: str
    timestamp: str
    source: str
    perception: dict[str, Any]
    decision: dict[str, Any]
    actions_taken: list[dict[str, Any]] = field(default_factory=list)
    annotated_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentOrchestrator:
    """Agentic Vision core: OpenCV evidence changes subsequent actions."""

    def __init__(
        self,
        detector: AnomalyDetector | None = None,
        policy: PolicyEngine | None = None,
        store: LocalEventStore | None = None,
        artifact_dir: Path | None = None,
    ):
        self.detector = detector or AnomalyDetector()
        self.policy = policy or PolicyEngine()
        self.store = store or LocalEventStore()
        self.artifact_dir = Path(artifact_dir or "fixtures/annotated")
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    def run_on_image(self, path: str | Path, source: str = "fixture") -> AgentTrace:
        path = Path(path)
        perception = self.detector.analyze_path(path)
        return self._complete(perception, source=source, stem=path.stem)

    def run_on_array(self, bgr, source: str = "webcam", stem: str = "frame", save_artifact: bool = True) -> AgentTrace:
        perception = self.detector.analyze(bgr)
        return self._complete(perception, source=source, stem=stem, save_artifact=save_artifact)

    def _complete(self, perception: DetectionResult, source: str, stem: str, save_artifact: bool = True) -> AgentTrace:
        ts = datetime.now(timezone.utc).isoformat()
        det_dict = perception.to_dict()
        decision = self.policy.decide(det_dict)

        annotated_path = None
        if save_artifact and perception.annotated_bgr is not None:
            import cv2

            annotated_path = str(self.artifact_dir / f"{stem}_annotated.jpg")
            cv2.imwrite(annotated_path, perception.annotated_bgr)

        actions = self._execute(decision, det_dict, source=source, annotated_path=annotated_path)
        raw = f"{ts}|{source}|{decision.action.value}|{det_dict.get('scene_hint')}"
        trace_id = hashlib.sha256(raw.encode()).hexdigest()[:16]

        trace = AgentTrace(
            trace_id=trace_id,
            timestamp=ts,
            source=source,
            perception=det_dict,
            decision=decision.to_dict(),
            actions_taken=actions,
            annotated_path=annotated_path,
        )
        self.store.append_trace(trace.to_dict())
        trace.annotated_bgr = perception.annotated_bgr  # in-memory only, not serialised
        return trace

    def _execute(
        self,
        decision: ActionDecision,
        perception: dict[str, Any],
        source: str,
        annotated_path: str | None,
    ) -> list[dict[str, Any]]:
        """Side effects driven by policy — this is the 'act' stage."""
        actions: list[dict[str, Any]] = []
        payload = build_event_payload(perception, decision.to_dict(), source, annotated_path)

        if decision.action == ActionKind.NOOP:
            actions.append({"type": "noop", "detail": "No cloud write."})
            return actions

        # Always persist structured event (local stand-in for S3/Dynamo via Lambda)
        ref = self.store.put_event(payload)
        actions.append({"type": "persist_event", "ref": ref, "backend": self.store.backend_name})

        if decision.action == ActionKind.AUTO_LOG:
            actions.append({"type": "audit_log", "detail": decision.reason})
        elif decision.action == ActionKind.NOTIFY:
            for who in decision.notify_targets:
                actions.append(
                    {
                        "type": "notify",
                        "target": who,
                        "channel": "sns_or_push_mock",
                        "message": decision.speakable_brief,
                    }
                )
        elif decision.action == ActionKind.HUMAN_REQUIRED:
            actions.append(
                {
                    "type": "escalate",
                    "targets": decision.notify_targets,
                    "requires_ack": True,
                    "message": decision.speakable_brief,
                }
            )
            actions.append({"type": "await_human", "detail": "Paused further automation until ack."})
        return actions
