"""API contract, AWS-honesty and evaluation regression tests.

These guard the claims made in the README / technical report:
- the UI is told AWS is *not* configured unless an ingest URL is really set,
- noop decisions are never forwarded, failures are surfaced (not hidden),
- bad input is rejected with the right status codes,
- the v2 detector keeps its held-out accuracy on a small deterministic sample.
"""

import base64

import pytest
from fastapi.testclient import TestClient

from northbridge_watch.api import server
from northbridge_watch.vision.scenes import SCENE_SPECS, list_scene_kinds

client = TestClient(server.app)


def test_health_reports_aws_not_configured_by_default(monkeypatch):
    monkeypatch.setattr(server, "AWS_INGEST_URL", "")
    d = client.get("/api/health").json()
    assert d["ok"] is True
    assert d["opencv"].startswith("5.")
    assert d["aws_ingest"] == "not_configured"
    assert d["household"] == ["Avery", "Morgan"]


def test_health_reports_configured_only_when_url_set(monkeypatch):
    monkeypatch.setattr(server, "AWS_INGEST_URL", "https://example.invalid/prod")
    assert client.get("/api/health").json()["aws_ingest"] == "configured"


def test_forward_skipped_when_not_configured(monkeypatch):
    monkeypatch.setattr(server, "AWS_INGEST_URL", "")
    assert server._forward_to_aws({"decision": {"action": "notify"}}) == {"configured": False}


def test_forward_never_sends_noop(monkeypatch):
    monkeypatch.setattr(server, "AWS_INGEST_URL", "https://example.invalid/prod")

    def boom(*a, **k):  # pragma: no cover - must not be called
        raise AssertionError("noop must not hit the network")

    monkeypatch.setattr(server.urllib.request, "urlopen", boom)
    out = server._forward_to_aws({"decision": {"action": "noop"}, "perception": {}})
    assert out["sent"] is False


def test_forward_failure_is_surfaced_not_hidden(monkeypatch):
    monkeypatch.setattr(server, "AWS_INGEST_URL", "https://example.invalid/prod")

    def fail(*a, **k):
        raise TimeoutError("simulated")

    monkeypatch.setattr(server.urllib.request, "urlopen", fail)
    out = server._forward_to_aws({"decision": {"action": "human_required"}, "perception": {}})
    assert out == {"configured": True, "sent": True, "ok": False, "error": "TimeoutError"}


def test_scenes_catalog_lists_all_five():
    ids = [s["id"] for s in client.get("/api/scenes").json()["scenes"]]
    assert ids == [k.value for k in list_scene_kinds()]
    assert len(ids) == 5


@pytest.mark.parametrize("kind", list_scene_kinds(), ids=lambda k: k.value)
def test_analyze_each_demo_scene_matches_expected_label(kind):
    d = client.post("/api/analyze", json={"scene": kind.value}).json()
    prim = d["trace"]["perception"]["primary"]
    got = prim["label"] if prim else "none"
    assert got == SCENE_SPECS[kind].expected_label
    assert d["server"]["opencv"].startswith("5.")


@pytest.mark.parametrize(
    "payload,status",
    [
        ({}, 400),
        ({"scene": "not_a_scene"}, 400),
        ({"image_b64": base64.b64encode(b"definitely not an image").decode()}, 400),
        ({"image_b64": base64.b64encode(b"\0" * (4 * 1024 * 1024 + 1)).decode()}, 413),
    ],
    ids=["empty", "unknown-scene", "undecodable", "too-large"],
)
def test_analyze_rejects_bad_input(payload, status):
    assert client.post("/api/analyze", json=payload).status_code == status


def test_heldout_accuracy_regression_small_sample():
    """Deterministic mini version of `make eval` (clean condition, 5 seeds per family).

    The full report numbers come from n=40/family; this only guards against regressions.
    """
    from northbridge_watch.eval.run_eval import evaluate
    from northbridge_watch.eval.synth import FAMILIES

    summary, rows = evaluate(FAMILIES, ["clean"], n=5)
    acc = summary["by_condition"]["clean"]["label_accuracy"]
    assert len(rows) == 5 * len(FAMILIES)
    assert acc >= 0.85, f"clean label accuracy regressed to {acc:.3f}"
