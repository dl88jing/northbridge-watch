"""Randomized synthetic scene generator for evaluation.

The canonical demo fixtures (vision/scenes.py) are five fixed images. This module draws
*randomized* variants of each scene family (positions, sizes, colours, counts, noise) plus
negative families (full fridge, clean floor) and out-of-domain families (coffee-coloured
spill, white poly-mailer package, night-time porch) so the detector is measured on images
it was not hand-tuned on.  Everything here is synthetic; see the report's limitations.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# family -> (expected primary label or "none", expected action under daytime policy)
FAMILIES: dict[str, tuple[str, str]] = {
    "calm_porch": ("none", "noop"),
    "package_at_door": ("package", "notify"),
    "busy_porch": ("package", "human_required"),
    "floor_spill": ("spill", "human_required"),
    "clean_floor": ("none", "noop"),
    "empty_fridge": ("empty_fridge", "notify"),
    "full_fridge": ("none", "noop"),
}

OOD_FAMILIES: dict[str, tuple[str, str]] = {
    "coffee_spill": ("spill", "human_required"),
    "white_mailer": ("package", "notify"),
    "night_porch_package": ("package", "notify"),
}


@dataclass
class Sample:
    family: str
    seed: int
    image: np.ndarray
    expected_label: str
    expected_action: str
    n_packages: int = 0


def _jit(rng: np.random.Generator, base: tuple[int, int, int], amt: int) -> tuple[int, int, int]:
    return tuple(int(np.clip(c + rng.integers(-amt, amt + 1), 0, 255)) for c in base)  # type: ignore[return-value]


def _porch(rng: np.random.Generator, h: int = 480, w: int = 640) -> np.ndarray:
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = _jit(rng, (210, 205, 198), 15)
    dx = int(rng.integers(-15, 16))
    cv2.rectangle(img, (220 + dx, 40), (420 + dx, 400), _jit(rng, (90, 70, 50), 15), -1)
    cv2.rectangle(img, (235 + dx, 55), (405 + dx, 385), (120, 95, 70), 2)
    cv2.circle(img, (390 + dx, 230), 8, (40, 180, 200), -1)
    cv2.rectangle(img, (180, 400), (460, 460), _jit(rng, (60, 80, 50), 10), -1)
    img[460:, :] = _jit(rng, (160, 155, 150), 10)
    return img


def _box(img, rng, x, y, bw, bh, colour=None):
    colour = colour or _jit(rng, (40, 90, 160), 15)
    edge = tuple(max(0, c - 40) for c in colour)
    tape = tuple(min(255, c + 20) for c in colour)
    cv2.rectangle(img, (x, y), (x + bw, y + bh), colour, -1)
    cv2.rectangle(img, (x, y), (x + bw, y + bh), edge, 2)
    cv2.line(img, (x, y + bh // 2), (x + bw, y + bh // 2), tape, 3)
    cv2.line(img, (x + bw // 2, y), (x + bw // 2, y + bh), tape, 3)


def _place_boxes(img, rng, n, colour=None) -> int:
    placed: list[tuple[int, int, int, int]] = []
    tries = 0
    while len(placed) < n and tries < 200:
        tries += 1
        bw, bh = int(rng.integers(75, 150)), int(rng.integers(50, 95))
        x, y = int(rng.integers(110, 600 - bw)), int(rng.integers(285, 470 - bh))
        if any(not (x + bw + 12 < px or px + pw + 12 < x or y + bh + 12 < py or py + ph + 12 < y)
               for px, py, pw, ph in placed):
            continue
        placed.append((x, y, bw, bh))
        _box(img, rng, x, y, bw, bh, colour)
    return len(placed)


def _floor(rng, h=480, w=640):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = _jit(rng, (230, 230, 225), 8)
    step = int(rng.integers(60, 100))
    line = _jit(rng, (200, 200, 195), 8)
    for i in range(0, w, step):
        cv2.line(img, (i, 0), (i, h), line, 2)
    for j in range(0, h, step):
        cv2.line(img, (0, j), (w, j), line, 2)
    return img


def _spill(img, rng, colour):
    cx, cy = int(rng.integers(160, 480)), int(rng.integers(150, 330))
    r = int(rng.integers(55, 115))
    k = int(rng.integers(6, 11))
    ang = np.sort(rng.uniform(0, 2 * np.pi, k))
    rad = r * rng.uniform(0.55, 1.2, k)
    pts = np.stack([cx + rad * np.cos(ang), cy + rad * np.sin(ang)], 1).astype(np.int32)
    ov = img.copy()
    cv2.fillPoly(ov, [pts], colour)
    a = float(rng.uniform(0.6, 0.8))
    cv2.addWeighted(ov, a, img, 1 - a, 0, img)


def _fridge(rng, n_items, h=480, w=640):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = _jit(rng, (25, 25, 25), 8)
    cv2.rectangle(img, (60, 40), (w - 60, h - 40), _jit(rng, (245, 245, 240), 6), -1)
    for y in (140, 260, 380):
        cv2.rectangle(img, (70, y), (w - 70, y + 8), (180, 180, 175), -1)
    for _ in range(n_items):
        x, y = int(rng.integers(90, 480)), int(rng.integers(60, 330))
        bw, bh = int(rng.integers(40, 110)), int(rng.integers(30, 70))
        col = tuple(int(c) for c in rng.integers(30, 230, 3))
        if rng.random() < 0.3:
            cv2.circle(img, (x + bw // 2, y + bh // 2), bh // 2, col, -1)
        else:
            cv2.rectangle(img, (x, y), (x + bw, y + bh), col, -1)
    cv2.rectangle(img, (w - 50, 40), (w - 20, h - 40), (160, 160, 155), -1)
    return img


def make_sample(family: str, seed: int) -> Sample:
    rng = np.random.default_rng(seed)
    exp_label, exp_action = {**FAMILIES, **OOD_FAMILIES}[family]
    n_pk = 0
    if family == "calm_porch":
        img = _porch(rng)
    elif family == "package_at_door":
        img = _porch(rng)
        n_pk = _place_boxes(img, rng, 1)
    elif family == "busy_porch":
        img = _porch(rng)
        n_pk = _place_boxes(img, rng, int(rng.integers(2, 5)))
    elif family == "floor_spill":
        img = _floor(rng)
        _spill(img, rng, _jit(rng, (200, 160, 40), 20))
    elif family == "clean_floor":
        img = _floor(rng)
    elif family == "empty_fridge":
        img = _fridge(rng, int(rng.integers(0, 2)))
    elif family == "full_fridge":
        img = _fridge(rng, int(rng.integers(5, 10)))
    elif family == "coffee_spill":
        img = _floor(rng)
        _spill(img, rng, _jit(rng, (40, 70, 110), 10))  # brown/coffee in BGR
    elif family == "white_mailer":
        img = _porch(rng)
        n_pk = _place_boxes(img, rng, 1, colour=_jit(rng, (235, 235, 235), 8))
    elif family == "night_porch_package":
        img = _porch(rng)
        n_pk = _place_boxes(img, rng, 1)
        img = cv2.convertScaleAbs(img, alpha=0.35, beta=0)
    else:
        raise ValueError(family)
    noise = rng.normal(0, 3, img.shape).astype(np.float32)
    img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return Sample(family, seed, img, exp_label, exp_action, n_pk)


# ---- perturbations (applied after generation) ---------------------------------------

def perturb(img: np.ndarray, condition: str, rng: np.random.Generator) -> np.ndarray:
    if condition == "clean":
        return img
    if condition == "photometric":
        alpha = float(rng.uniform(0.8, 1.2))
        beta = float(rng.uniform(-35, 35))
        return cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
    if condition == "blur_noise":
        out = cv2.GaussianBlur(img, (5, 5), 0).astype(np.float32)
        out += rng.normal(0, 10, img.shape)
        return np.clip(out, 0, 255).astype(np.uint8)
    if condition == "jpeg_q30":
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 30])
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if condition == "half_res":
        return cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2), interpolation=cv2.INTER_AREA)
    raise ValueError(condition)


CONDITIONS = ["clean", "photometric", "blur_noise", "jpeg_q30", "half_res"]
