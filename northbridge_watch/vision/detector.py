"""OpenCV 5 anomaly detection for Northbridge Watch demo scenes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]
    area: float
    notes: str = ""


@dataclass
class DetectionResult:
    scene_hint: str
    detections: list[Detection] = field(default_factory=list)
    opencv_version: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    annotated_bgr: np.ndarray | None = None

    @property
    def primary(self) -> Detection | None:
        if not self.detections:
            return None
        return max(self.detections, key=lambda d: d.confidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_hint": self.scene_hint,
            "opencv_version": self.opencv_version or cv2.__version__,
            "detections": [asdict(d) for d in self.detections],
            "metrics": self.metrics,
            "primary": asdict(self.primary) if self.primary else None,
        }


class AnomalyDetector:
    def __init__(self, min_package_area: int = 2000, min_spill_area: int = 5000):
        self.min_package_area = min_package_area
        self.min_spill_area = min_spill_area
        self.opencv_version = cv2.__version__

    def analyze_path(self, path: str | Path) -> DetectionResult:
        img = cv2.imread(str(path))
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {path}")
        return self.analyze(img)

    def analyze(self, bgr: np.ndarray) -> DetectionResult:
        context = self._scene_context(bgr)
        packages = self._detect_packages(bgr) if context["porch_like"] else []
        spills = self._detect_spills(bgr) if context["floor_like"] else []
        fridge = self._detect_empty_fridge(bgr) if context["fridge_like"] else []
        candidates = packages + spills + fridge
        if not candidates:
            result = DetectionResult(
                scene_hint="calm",
                detections=[],
                opencv_version=self.opencv_version,
                metrics={"signal": 0.0, **context},
            )
            result.annotated_bgr = self._annotate(bgr, result)
            return result
        primary = max(candidates, key=lambda d: d.confidence)
        hint_map = {"package": "porch_package", "spill": "floor_spill", "empty_fridge": "empty_fridge"}
        result = DetectionResult(
            scene_hint=hint_map.get(primary.label, "unknown"),
            detections=sorted(candidates, key=lambda d: -d.confidence),
            opencv_version=self.opencv_version,
            metrics={
                "n_detections": len(candidates),
                "max_confidence": primary.confidence,
                "opencv": self.opencv_version,
                **context,
            },
        )
        result.annotated_bgr = self._annotate(bgr, result)
        return result

    def _scene_context(self, bgr: np.ndarray) -> dict[str, Any]:
        h, w = bgr.shape[:2]
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        border = np.concatenate(
            [gray[:12, :].ravel(), gray[-12:, :].ravel(), gray[:, :12].ravel(), gray[:, -12:].ravel()]
        )
        center = gray[int(h * 0.2) : int(h * 0.8), int(w * 0.15) : int(w * 0.85)]
        border_mean = float(np.mean(border))
        center_mean = float(np.mean(center))
        door_roi = gray[40:400, 220:420]
        door_dark = float(np.mean(door_roi)) < 120 if door_roi.size else False
        mat_roi = bgr[400:460, 180:460]
        mat_green = False
        if mat_roi.size:
            mat_hsv = cv2.cvtColor(mat_roi, cv2.COLOR_BGR2HSV)
            greenish = (
                (mat_hsv[:, :, 0] > 35)
                & (mat_hsv[:, :, 0] < 95)
                & (mat_hsv[:, :, 1] > 50)
                & (mat_hsv[:, :, 2] > 40)
            )
            mat_green = float(np.mean(greenish)) > 0.15
        porch_like = bool(door_dark or mat_green)
        horizontal = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        vertical = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        grid_score = float(np.mean(np.abs(horizontal) > 40) + np.mean(np.abs(vertical) > 40))
        floor_like = (not porch_like) and center_mean > 180 and grid_score > 0.08 and border_mean > 150
        fridge_like = border_mean < 80 and center_mean > 180 and not porch_like
        return {
            "porch_like": porch_like,
            "floor_like": bool(floor_like),
            "fridge_like": bool(fridge_like),
            "border_mean": round(border_mean, 1),
            "center_mean": round(center_mean, 1),
            "grid_score": round(grid_score, 3),
        }

    def _detect_packages(self, bgr: np.ndarray) -> list[Detection]:
        h, _w = bgr.shape[:2]
        roi = bgr[int(h * 0.45) :, :]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        lower = np.array([8, 50, 40])
        upper = np.array([25, 255, 230])
        mask = cv2.inRange(hsv, lower, upper)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out: list[Detection] = []
        y_off = int(h * 0.45)
        for cnt in contours:
            area = float(cv2.contourArea(cnt))
            if area < self.min_package_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / max(bh, 1)
            if aspect < 0.5 or aspect > 3.5:
                continue
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
            rect_score = 1.0 if len(approx) <= 8 else 0.7
            conf = float(min(0.82, 0.45 + (area / 25000.0) * rect_score))
            if conf < 0.4:
                continue
            out.append(
                Detection(
                    label="package",
                    confidence=round(conf, 3),
                    bbox=(x, y + y_off, bw, bh),
                    area=area,
                    notes=f"approx_vertices={len(approx)} aspect={aspect:.2f}",
                )
            )
        return self._merge_packages(out)

    def _merge_packages(self, dets: list[Detection]) -> list[Detection]:
        if len(dets) <= 1:
            return dets
        boxes = [list(d.bbox) + [d.area, d.confidence, d.notes] for d in dets]
        changed = True
        while changed:
            changed = False
            nxt: list[list] = []
            used = [False] * len(boxes)
            for i, a in enumerate(boxes):
                if used[i]:
                    continue
                ax, ay, aw, ah, aarea, aconf, anotes = a
                for j in range(i + 1, len(boxes)):
                    if used[j]:
                        continue
                    bx, by, bw, bh, barea, bconf, _bnotes = boxes[j]
                    pad = 2
                    ar = (ax - pad, ay - pad, ax + aw + pad, ay + ah + pad)
                    br = (bx - pad, by - pad, bx + bw + pad, by + bh + pad)
                    ix0, iy0 = max(ar[0], br[0]), max(ar[1], br[1])
                    ix1, iy1 = min(ar[2], br[2]), min(ar[3], br[3])
                    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
                    smaller = min(aw * ah, bw * bh) or 1
                    # Only merge strong overlaps (tape splits), not neighboring boxes
                    if inter / smaller > 0.3:
                        nx0, ny0 = min(ax, bx), min(ay, by)
                        nx1, ny1 = max(ax + aw, bx + bw), max(ay + ah, by + bh)
                        ax, ay, aw, ah = nx0, ny0, nx1 - nx0, ny1 - ny0
                        aarea += barea
                        aconf = max(aconf, bconf)
                        used[j] = True
                        changed = True
                nxt.append([ax, ay, aw, ah, aarea, aconf, anotes])
                used[i] = True
            boxes = nxt
        out: list[Detection] = []
        for x, y, bw, bh, area, _conf, notes in boxes:
            conf = float(min(0.82, 0.5 + area / 40000.0))
            out.append(
                Detection(
                    label="package",
                    confidence=round(conf, 3),
                    bbox=(int(x), int(y), int(bw), int(bh)),
                    area=float(area),
                    notes=str(notes) + "|merged",
                )
            )
        return out

    def _detect_spills(self, bgr: np.ndarray) -> list[Detection]:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        lower = np.array([85, 50, 40])
        upper = np.array([130, 255, 230])
        mask = cv2.inRange(hsv, lower, upper)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out: list[Detection] = []
        for cnt in contours:
            area = float(cv2.contourArea(cnt))
            if area < self.min_spill_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            hull = cv2.convexHull(cnt)
            hull_area = float(cv2.contourArea(hull)) or 1.0
            solidity = area / hull_area
            irregular = 1.0 - min(solidity, 1.0)
            conf = float(min(0.95, 0.4 + (area / 25000.0) * 0.35 + irregular * 0.4))
            if conf < 0.45:
                continue
            out.append(
                Detection(
                    label="spill",
                    confidence=round(conf, 3),
                    bbox=(x, y, bw, bh),
                    area=area,
                    notes=f"solidity={solidity:.2f}",
                )
            )
        return out

    def _detect_empty_fridge(self, bgr: np.ndarray) -> list[Detection]:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        center = gray[int(h * 0.15) : int(h * 0.85), int(w * 0.12) : int(w * 0.85)]
        mean_bright = float(np.mean(center))
        if mean_bright < 170:
            return []
        edges = cv2.Canny(center, 60, 150)
        horizontal = cv2.Sobel(center, cv2.CV_32F, 0, 1, ksize=3)
        shelf_score = float(np.mean(np.abs(horizontal) > 50))
        edge_density = float(np.count_nonzero(edges)) / max(edges.size, 1)
        emptiness = max(0.0, 1.0 - edge_density * 10.0)
        if shelf_score < 0.02:
            return []
        conf = float(
            min(0.93, (mean_bright / 255.0) * 0.35 + emptiness * 0.45 + min(shelf_score, 0.1) * 2)
        )
        if conf < 0.55:
            return []
        return [
            Detection(
                label="empty_fridge",
                confidence=round(conf, 3),
                bbox=(int(w * 0.12), int(h * 0.15), int(w * 0.73), int(h * 0.7)),
                area=float(center.size),
                notes=f"mean_bright={mean_bright:.1f} edge_density={edge_density:.4f} shelf={shelf_score:.3f}",
            )
        ]

    def _annotate(self, bgr: np.ndarray, result: DetectionResult) -> np.ndarray:
        out = bgr.copy()
        colors = {"package": (40, 140, 255), "spill": (30, 90, 220), "empty_fridge": (180, 120, 40)}
        for det in result.detections:
            x, y, bw, bh = det.bbox
            color = colors.get(det.label, (0, 255, 0))
            cv2.rectangle(out, (x, y), (x + bw, y + bh), color, 2)
            tag = f"{det.label} {det.confidence:.2f}"
            cv2.putText(out, tag, (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        banner = f"OpenCV {self.opencv_version} | {result.scene_hint}"
        cv2.rectangle(out, (0, 0), (out.shape[1], 28), (30, 30, 30), -1)
        cv2.putText(out, banner, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)
        return out
