"""AWS Lambda-shaped handler + local event store.

Production path (documented in docs/aws-deploy.md):
  API Gateway → Lambda (this handler) → S3 (events + optional frames) + optional SNS.

Judges can run fully offline via LocalEventStore (JSONL under fixtures/events/).
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_event_payload(
    perception: dict[str, Any],
    decision: dict[str, Any],
    source: str,
    annotated_path: str | None = None,
) -> dict[str, Any]:
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "perception": perception,
        "decision": decision,
        "annotated_path": annotated_path,
        "household": "Northbridge",
        "members": ["Avery", "Morgan"],
    }


class LocalEventStore:
    """Offline stand-in for S3 + DynamoDB used by the agent loop."""

    def __init__(self, root: Path | None = None):
        self.root = Path(root or os.environ.get("NW_EVENT_DIR", "fixtures/events"))
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_path = self.root / "events.jsonl"
        self.traces_path = self.root / "traces.jsonl"
        self.backend_name = "local-jsonl"

    def put_event(self, payload: dict[str, Any]) -> str:
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
        return f"local://{self.events_path.name}#{payload['event_id']}"

    def append_trace(self, trace: dict[str, Any]) -> None:
        with self.traces_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(trace) + "\n")

    def list_events(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            return []
        lines = self.events_path.read_text(encoding="utf-8").strip().splitlines()
        out = [json.loads(x) for x in lines[-limit:]]
        return list(reversed(out))

    def list_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.traces_path.exists():
            return []
        lines = self.traces_path.read_text(encoding="utf-8").strip().splitlines()
        out = [json.loads(x) for x in lines[-limit:]]
        return list(reversed(out))


def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """API Gateway proxy integration entrypoint.

    Expected body JSON:
      {
        "perception": {...},   # from OpenCV edge / worker
        "decision": {...},     # optional; if absent, Lambda can re-run policy
        "source": "edge|webcam|fixture",
        "annotated_s3_key": "optional"
      }

    When AWS credentials + bucket are configured, writes to S3.
    Otherwise falls back to LocalEventStore (safe for demos).
    """
    try:
        body = event.get("body", event)
        if isinstance(body, str):
            body = json.loads(body or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Invalid JSON body"})

    perception = body.get("perception") or {}
    decision = body.get("decision")
    source = body.get("source", "api")
    annotated = body.get("annotated_s3_key") or body.get("annotated_path")

    if decision is None:
        from northbridge_watch.agent.policy import PolicyEngine

        decision = PolicyEngine().decide(perception).to_dict()

    payload = build_event_payload(perception, decision, source, annotated)
    bucket = os.environ.get("NW_S3_BUCKET")
    if bucket:
        try:
            import boto3

            s3 = boto3.client("s3")
            key = f"events/{payload['event_id']}.json"
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(payload).encode("utf-8"),
                ContentType="application/json",
            )
            # Optional SNS notify
            topic = os.environ.get("NW_SNS_TOPIC_ARN")
            if topic and decision.get("action") in ("notify", "human_required"):
                sns = boto3.client("sns")
                sns.publish(
                    TopicArn=topic,
                    Subject=f"Northbridge Watch: {decision.get('action')}",
                    Message=decision.get("speakable_brief") or json.dumps(decision),
                )
            return _response(200, {"ok": True, "ref": f"s3://{bucket}/{key}", "event": payload})
        except Exception as exc:  # noqa: BLE001 — surface for judges
            return _response(500, {"error": str(exc), "hint": "Check IAM / bucket"})

    store = LocalEventStore()
    ref = store.put_event(payload)
    return _response(200, {"ok": True, "ref": ref, "event": payload, "backend": "local"})


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }
