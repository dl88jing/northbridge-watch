import json

from northbridge_watch.agent.orchestrator import AgentOrchestrator
from northbridge_watch.aws.handler import LocalEventStore, lambda_handler
from northbridge_watch.vision.scenes import SceneKind, generate_scene


def test_noop_scene_writes_no_event(tmp_path):
    store = LocalEventStore(tmp_path)
    orch = AgentOrchestrator(store=store, artifact_dir=tmp_path)
    tr = orch.run_on_array(generate_scene(SceneKind.CALM_PORCH), stem="calm")
    assert tr.decision["action"] == "noop"
    assert store.list_events() == []
    assert len(store.list_traces()) == 1


def test_spill_scene_persists_and_escalates(tmp_path):
    store = LocalEventStore(tmp_path)
    orch = AgentOrchestrator(store=store, artifact_dir=tmp_path)
    tr = orch.run_on_array(generate_scene(SceneKind.FLOOR_SPILL), stem="spill")
    types = [a["type"] for a in tr.actions_taken]
    assert "persist_event" in types and "escalate" in types and "await_human" in types
    assert len(store.list_events()) == 1


def test_lambda_ingest_local_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("NW_S3_BUCKET", raising=False)
    monkeypatch.setenv("NW_EVENT_DIR", str(tmp_path))
    perception = {"primary": {"label": "spill", "confidence": 0.7}, "detections": [{"label": "spill", "confidence": 0.7}]}
    out = lambda_handler({"body": json.dumps({"perception": perception, "source": "test"})})
    body = json.loads(out["body"])
    assert out["statusCode"] == 200 and body["ok"]
    assert body["event"]["decision"]["action"] == "human_required"


def test_lambda_rejects_bad_json():
    assert lambda_handler({"body": "{not json"})["statusCode"] == 400


def test_lambda_health_route_does_not_write_event():
    from northbridge_watch.aws.handler import lambda_handler
    import json as _json
    r = lambda_handler({"httpMethod": "GET", "path": "/health"})
    assert r["statusCode"] == 200
    assert _json.loads(r["body"])["service"] == "northbridge-watch-ingest"


def test_upload_is_not_written_to_disk(tmp_path, monkeypatch):
    import base64
    from fastapi.testclient import TestClient
    from northbridge_watch.api import server
    from northbridge_watch.vision.scenes import SceneKind, generate_scene
    import cv2
    ok, enc = cv2.imencode(".jpg", generate_scene(SceneKind.FLOOR_SPILL))
    before = set(server.ANNOTATED.glob("upload*"))
    r = TestClient(server.app).post("/api/analyze", json={"image_b64": base64.b64encode(enc.tobytes()).decode()})
    assert r.status_code == 200
    d = r.json()
    assert d["trace"]["decision"]["action"] == "human_required"
    assert d["annotated_b64"].startswith("data:image/jpeg;base64,")
    assert set(server.ANNOTATED.glob("upload*")) == before
