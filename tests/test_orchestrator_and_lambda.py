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
