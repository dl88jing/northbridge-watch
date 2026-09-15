"""Local FastAPI control plane — mirrors judge-facing contracts used by the web UI."""

from __future__ import annotations

import base64
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
FIXTURES = ROOT / "fixtures" / "scenes"
ANNOTATED = ROOT / "fixtures" / "annotated"

app = FastAPI(title="Northbridge Watch", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orch = AgentOrchestrator(artifact_dir=ANNOTATED)
store = LocalEventStore(ROOT / "fixtures" / "events")


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
    if body.image_b64:
        import numpy as np

        raw = base64.b64decode(body.image_b64.split(",")[-1])
        arr = np.frombuffer(raw, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            raise HTTPException(400, "Could not decode image")
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

    annotated_b64 = None
    if trace.annotated_path and Path(trace.annotated_path).exists():
        data = Path(trace.annotated_path).read_bytes()
        annotated_b64 = "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")

    return {"trace": trace.to_dict(), "annotated_b64": annotated_b64}


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
