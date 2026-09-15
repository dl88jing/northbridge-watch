"""SAM packaging entry — re-export Lambda handler.

Deploy notes:
  sam build && sam deploy --guided

For full OpenCV 5 on Lambda/Graviton, attach a custom layer or container image
with opencv-python-headless==5.0.0.93 (see docs/aws-deploy.md). The default
ingest path accepts precomputed perception JSON from the edge worker so the
Lambda stays light and the OpenCV work can also run on EC2/Graviton + COOL.
"""

from __future__ import annotations

import json
from typing import Any


def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    path = (event.get("rawPath") or event.get("path") or "").rstrip("/")
    if path.endswith("/health") or event.get("httpMethod") == "GET" and "health" in path:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"ok": True, "service": "northbridge-watch", "team": "Northbridge"}),
        }

    # Prefer in-repo handler when packaged as a full zip; otherwise inline minimal path
    try:
        from northbridge_watch.aws.handler import lambda_handler as impl

        return impl(event, context)
    except ImportError:
        body = event.get("body", "{}")
        if isinstance(body, str):
            try:
                payload = json.loads(body or "{}")
            except json.JSONDecodeError:
                return _resp(400, {"error": "bad json"})
        else:
            payload = body
        # Echo + stamp — full S3 path requires northbridge_watch package in the deployment artifact
        return _resp(
            200,
            {
                "ok": True,
                "mode": "lite",
                "received_keys": list(payload.keys()),
                "hint": "Package northbridge_watch for S3/SNS persistence",
            },
        )


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body),
    }
