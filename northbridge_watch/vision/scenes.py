"""Synthetic demo scenes for Northbridge Watch (no third-party stock required)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable

import zlib

import cv2
import numpy as np


class SceneKind(str, Enum):
    CALM_PORCH = "calm_porch"
    PACKAGE_AT_DOOR = "package_at_door"
    FLOOR_SPILL = "floor_spill"
    EMPTY_FRIDGE = "empty_fridge"
    BUSY_PORCH = "busy_porch"


@dataclass(frozen=True)
class SceneSpec:
    kind: SceneKind
    title: str
    description: str
    expected_label: str


SCENE_SPECS: dict[SceneKind, SceneSpec] = {
    SceneKind.CALM_PORCH: SceneSpec(
        SceneKind.CALM_PORCH,
        "Calm porch",
        "Empty Northbridge porch — no action expected.",
        "none",
    ),
    SceneKind.PACKAGE_AT_DOOR: SceneSpec(
        SceneKind.PACKAGE_AT_DOOR,
        "Package at door",
        "Single brown package on the porch mat.",
        "package",
    ),
    SceneKind.FLOOR_SPILL: SceneSpec(
        SceneKind.FLOOR_SPILL,
        "Kitchen spill",
        "Irregular liquid spill on light tile.",
        "spill",
    ),
    SceneKind.EMPTY_FRIDGE: SceneSpec(
        SceneKind.EMPTY_FRIDGE,
        "Empty fridge shelf",
        "Mostly empty fridge interior — restock signal.",
        "empty_fridge",
    ),
    SceneKind.BUSY_PORCH: SceneSpec(
        SceneKind.BUSY_PORCH,
        "Busy porch (multi-package)",
        "Several packages blocking the door — notify Avery & Morgan.",
        "package",
    ),
}


def list_scene_kinds() -> list[SceneKind]:
    return list(SceneKind)


def _draw_porch_base(h: int = 480, w: int = 640) -> np.ndarray:
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = (210, 205, 198)
    cv2.rectangle(img, (220, 40), (420, 400), (90, 70, 50), -1)
    cv2.rectangle(img, (235, 55), (405, 385), (120, 95, 70), 2)
    cv2.circle(img, (390, 230), 8, (40, 180, 200), -1)
    cv2.rectangle(img, (180, 400), (460, 460), (60, 80, 50), -1)
    cv2.putText(img, "NORTHBRIDGE", (205, 435), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 220, 180), 1)
    img[460:, :] = (160, 155, 150)
    return img


def _draw_package(img: np.ndarray, x: int, y: int, bw: int, bh: int, label: str = "") -> None:
    cv2.rectangle(img, (x, y), (x + bw, y + bh), (40, 90, 160), -1)
    cv2.rectangle(img, (x, y), (x + bw, y + bh), (20, 50, 90), 2)
    mid = y + bh // 2
    # Tape close to cardboard hue so contour stays one blob
    cv2.line(img, (x, mid), (x + bw, mid), (50, 120, 180), 3)
    cv2.line(img, (x + bw // 2, y), (x + bw // 2, y + bh), (50, 120, 180), 3)
    if label:
        cv2.putText(img, label, (x + 6, y + bh - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)


def _draw_spill(img: np.ndarray) -> np.ndarray:
    img[:] = (230, 230, 225)
    for i in range(0, img.shape[1], 80):
        cv2.line(img, (i, 0), (i, img.shape[0]), (200, 200, 195), 2)
    for j in range(0, img.shape[0], 80):
        cv2.line(img, (0, j), (img.shape[1], j), (200, 200, 195), 2)
    overlay = img.copy()
    pts = np.array(
        [[180, 220], [260, 190], [340, 230], [360, 300], [280, 340], [200, 310], [160, 260]],
        dtype=np.int32,
    )
    # BGR cyan/blue spill (HSV ~100)
    cv2.fillPoly(overlay, [pts], (200, 160, 40))
    cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)
    cv2.ellipse(img, (250, 250), (40, 18), 20, 0, 360, (230, 200, 120), -1)
    return img


def _draw_fridge(img: np.ndarray, empty: bool = True) -> np.ndarray:
    h, w = img.shape[:2]
    img[:] = (25, 25, 25)
    cv2.rectangle(img, (60, 40), (w - 60, h - 40), (245, 245, 240), -1)
    for y in (140, 260, 380):
        cv2.rectangle(img, (70, y), (w - 70, y + 8), (180, 180, 175), -1)
    if not empty:
        cv2.rectangle(img, (100, 80), (200, 120), (80, 160, 60), -1)
        cv2.rectangle(img, (220, 90), (300, 125), (60, 60, 200), -1)
        cv2.circle(img, (380, 100), 28, (50, 50, 220), -1)
        cv2.rectangle(img, (120, 180), (280, 240), (200, 180, 100), -1)
    else:
        cv2.rectangle(img, (300, 300), (340, 360), (100, 140, 180), -1)
        cv2.putText(img, "?", (308, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.rectangle(img, (w - 50, 40), (w - 20, h - 40), (160, 160, 155), -1)
    return img


def generate_scene(kind: SceneKind, seed: int = 7) -> np.ndarray:
    # zlib.crc32 is stable across processes (built-in hash() is salted per run)
    rng = np.random.default_rng(seed + zlib.crc32(kind.value.encode()) % 1000)
    if kind == SceneKind.CALM_PORCH:
        img = _draw_porch_base()
    elif kind == SceneKind.PACKAGE_AT_DOOR:
        img = _draw_porch_base()
        _draw_package(img, 250, 330, 140, 90, "AMZ")
    elif kind == SceneKind.BUSY_PORCH:
        img = _draw_porch_base()
        # Separated boxes so contours do not merge
        _draw_package(img, 150, 360, 90, 60, "A")
        _draw_package(img, 410, 355, 95, 65, "B")
        _draw_package(img, 280, 285, 85, 55, "C")
    elif kind == SceneKind.FLOOR_SPILL:
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        _draw_spill(img)
    elif kind == SceneKind.EMPTY_FRIDGE:
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        _draw_fridge(img, empty=True)
    else:
        raise ValueError(kind)
    noise = rng.normal(0, 3, img.shape).astype(np.float32)
    return np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def write_scene_fixtures(out_dir: Path, kinds: Iterable[SceneKind] | None = None) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for kind in kinds or list_scene_kinds():
        img = generate_scene(kind)
        path = out_dir / f"{kind.value}.jpg"
        cv2.imwrite(str(path), img)
        paths.append(path)
    return paths
