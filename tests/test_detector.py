import cv2
import numpy as np
import pytest

from northbridge_watch.eval.synth import make_sample
from northbridge_watch.vision.detector import AnomalyDetector
from northbridge_watch.vision.scenes import SCENE_SPECS, SceneKind, generate_scene


@pytest.fixture(scope="module")
def det():
    return AnomalyDetector()


@pytest.mark.parametrize("kind", list(SceneKind))
def test_canonical_fixtures_match_expected_label(det, kind):
    res = det.analyze(generate_scene(kind)).to_dict()
    pred = res["primary"]["label"] if res["primary"] else "none"
    assert pred == SCENE_SPECS[kind].expected_label


def test_busy_porch_counts_three_packages(det):
    res = det.analyze(generate_scene(SceneKind.BUSY_PORCH)).to_dict()
    assert sum(d["label"] == "package" for d in res["detections"]) == 3


def test_scene_generation_is_deterministic():
    a = generate_scene(SceneKind.PACKAGE_AT_DOOR)
    b = generate_scene(SceneKind.PACKAGE_AT_DOOR)
    assert np.array_equal(a, b)


def test_opencv_major_version_is_5(det):
    assert cv2.__version__.startswith("5."), cv2.__version__
    assert det.analyze(generate_scene(SceneKind.CALM_PORCH)).to_dict()["opencv_version"] == cv2.__version__


def test_full_fridge_is_not_reported_empty(det):
    # Regression for the v1 bug: a stocked fridge was flagged empty_fridge 40/40 times.
    for seed in range(7, 17):
        res = det.analyze(make_sample("full_fridge", seed).image).to_dict()
        assert (res["primary"] or {}).get("label") != "empty_fridge"


@pytest.mark.parametrize("size", [(320, 240), (1280, 960)])
def test_resolution_is_normalised(det, size):
    img = cv2.resize(generate_scene(SceneKind.PACKAGE_AT_DOOR), size)
    res = det.analyze(img).to_dict()
    assert res["primary"]["label"] == "package"
    assert res["metrics"]["input_size"] == list(size)


def test_annotated_frame_is_produced(det):
    r = det.analyze(generate_scene(SceneKind.FLOOR_SPILL))
    assert r.annotated_bgr is not None and r.annotated_bgr.shape == (480, 640, 3)


def test_blank_image_is_calm(det):
    res = det.analyze(np.full((480, 640, 3), 128, np.uint8)).to_dict()
    assert res["primary"] is None
