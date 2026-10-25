from datetime import datetime, timezone

from northbridge_watch.agent.policy import ActionKind, PolicyEngine

DAY = datetime(2026, 9, 15, 15, 0, tzinfo=timezone.utc)
NIGHT = datetime(2026, 9, 15, 23, 30, tzinfo=timezone.utc)


def det(label, conf=0.8, n=1):
    ds = [{"label": label, "confidence": conf, "bbox": [0, 0, 1, 1], "area": 1.0}] * n
    return {"primary": ds[0], "detections": ds}


def test_no_detection_is_noop():
    assert PolicyEngine().decide({"primary": None, "detections": []}, now=DAY).action == ActionKind.NOOP


def test_spill_always_escalates_even_at_night():
    for now in (DAY, NIGHT):
        d = PolicyEngine().decide(det("spill", 0.5), now=now)
        assert d.action == ActionKind.HUMAN_REQUIRED and d.requires_ack


def test_multi_package_requires_human():
    d = PolicyEngine().decide(det("package", 0.7, n=3), now=DAY)
    assert d.action == ActionKind.HUMAN_REQUIRED
    assert set(d.notify_targets) == {"Avery", "Morgan"}


def test_single_package_notifies_by_day_and_logs_at_night():
    assert PolicyEngine().decide(det("package"), now=DAY).action == ActionKind.NOTIFY
    assert PolicyEngine().decide(det("package"), now=NIGHT).action == ActionKind.AUTO_LOG


def test_low_confidence_package_is_only_logged():
    assert PolicyEngine().decide(det("package", 0.3), now=DAY).action == ActionKind.AUTO_LOG


def test_empty_fridge_quiet_hours():
    assert PolicyEngine().decide(det("empty_fridge"), now=DAY).action == ActionKind.NOTIFY
    assert PolicyEngine().decide(det("empty_fridge"), now=NIGHT).action == ActionKind.AUTO_LOG


def test_unknown_label_safe_default():
    assert PolicyEngine().decide(det("raccoon"), now=DAY).action == ActionKind.AUTO_LOG
