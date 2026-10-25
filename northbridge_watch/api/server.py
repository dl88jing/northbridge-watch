"""Local FastAPI control plane — mirrors judge-facing contracts used by the web UI."""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any

import cv2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from northbridge_watch import HOUSEHOLD, TEAM, __version__
from northbridge_watch.agent.orchestrator import AgentOrchestrator
from northbridge_watch.aws.handler import LocalEventStore
from northbridge_watch.vision.scenes import SCENE_SPECS, SceneKind, generate_scene, list_scene_kinds

ROOT = Path(__file__).resolve().parents[2]
# On serverless hosts (Vercel) only /tmp is writable; NW_* env vars redirect artifacts there.
FIXTURES = Path(os.environ.get("NW_FIXTURE_DIR", ROOT / "fixtures" / "scenes"))
ANNOTATED = Path(os.environ.get("NW_ARTIFACT_DIR", ROOT / "fixtures" / "annotated"))
EVENTS = Path(os.environ.get("NW_EVENT_DIR", ROOT / "fixtures" / "events"))
# Optional: the AWS API Gateway /ingest URL (set as a Vercel env var, never committed).
AWS_INGEST_URL = os.environ.get("NW_AWS_INGEST_URL", "").strip()
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_SIDE = 4096

app = FastAPI(title="Northbridge Watch", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store = LocalEventStore(EVENTS)
orch = AgentOrchestrator(artifact_dir=ANNOTATED, store=store)


def _host() -> str:
    if os.environ.get("VERCEL"):
        return "vercel-serverless"
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return "aws-lambda"
    return "local"


def _forward_to_aws(trace: dict[str, Any]) -> dict[str, Any]:
    """Send the perception+decision to the AWS ingest Lambda (S3 + SNS) when configured."""
    if not AWS_INGEST_URL:
        return {"configured": False}
    if trace["decision"]["action"] == "noop":
        return {"configured": True, "sent": False, "reason": "noop: nothing to persist"}
    body = json.dumps(
        {"perception": trace["perception"], "decision": trace["decision"], "source": "vercel-ui"}
    ).encode()
    req = urllib.request.Request(
        AWS_INGEST_URL.rstrip("/") + "/ingest",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            out = json.loads(r.read().decode() or "{}")
        return {
            "configured": True,
            "sent": True,
            "ok": bool(out.get("ok")),
            "ref": out.get("ref"),
            "ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as exc:  # noqa: BLE001 — surface honestly in the UI
        return {"configured": True, "sent": True, "ok": False, "error": type(exc).__name__}


class AnalyzeBody(BaseModel):
    scene: str | None = None
    image_b64: str | None = Field(None, description="Optional JPEG/PNG base64")


@app.get("/api/health")
def health() -> dict[str, Any]:
    import cv2 as _cv

    return {
        "ok": True,
        "version": __version__,
        "team": TEAM,
        "household": list(HOUSEHOLD),
        "opencv": _cv.__version__,
        "path": "Agentic Vision",
        "host": _host(),
        "aws_ingest": "configured" if AWS_INGEST_URL else "not_configured",
    }


@app.get("/api/scenes")
def scenes() -> dict[str, Any]:
    items = []
    for kind in list_scene_kinds():
        spec = SCENE_SPECS[kind]
        path = FIXTURES / f"{kind.value}.jpg"
        items.append(
            {
                "id": kind.value,
                "title": spec.title,
                "description": spec.description,
                "expected_label": spec.expected_label,
                "fixture": path.exists(),
            }
        )
    return {"scenes": items}


@app.post("/api/analyze")
def analyze(body: AnalyzeBody) -> dict[str, Any]:
    t0 = time.perf_counter()
    if body.image_b64:
        import numpy as np

        try:
            raw = base64.b64decode(body.image_b64.split(",")[-1], validate=False)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, "Invalid base64") from exc
        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Image larger than 4 MB")
        arr = np.frombuffer(raw, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            raise HTTPException(400, "Could not decode image")
        if max(bgr.shape[:2]) > MAX_SIDE:
            raise HTTPException(413, f"Image side larger than {MAX_SIDE}px")
        trace = orch.run_on_array(bgr, source="upload", stem="upload")
    elif body.scene:
        try:
            kind = SceneKind(body.scene)
        except ValueError as exc:
            raise HTTPException(400, f"Unknown scene: {body.scene}") from exc
        path = FIXTURES / f"{kind.value}.jpg"
        if not path.exists():
            FIXTURES.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(path), generate_scene(kind))
        trace = orch.run_on_image(path, source="fixture")
    else:
        raise HTTPException(400, "Provide scene or image_b64")

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    annotated_b64 = None
    if trace.annotated_path and Path(trace.annotated_path).exists():
        data = Path(trace.annotated_path).read_bytes()
        annotated_b64 = "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")

    tdict = trace.to_dict()
    return {
        "trace": tdict,
        "annotated_b64": annotated_b64,
        "server": {"host": _host(), "opencv": cv2.__version__, "pipeline_ms": elapsed_ms},
        "aws": _forward_to_aws(tdict),
    }


@app.get("/api/traces")
def traces(limit: int = 20) -> dict[str, Any]:
    return {"traces": store.list_traces(limit)}


@app.get("/api/events")
def events(limit: int = 20) -> dict[str, Any]:
    return {"events": store.list_events(limit)}


def main() -> None:
    import uvicorn

    uvicorn.run("northbridge_watch.api.server:app", host="127.0.0.1", port=8787, reload=False)


if __name__ == "__main__":
    main()
