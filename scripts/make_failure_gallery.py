"""Render real failure cases from the held-out eval (docs/eval/rows.csv) into docs/failures/."""
from __future__ import annotations
import csv
from pathlib import Path
import cv2
import numpy as np
from northbridge_watch.eval.synth import make_sample, perturb
from northbridge_watch.vision.detector import AnomalyDetector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "failures"
WANT = [("clean", "floor_spill"), ("photometric", "floor_spill"), ("clean", "empty_fridge"),
        ("photometric", "full_fridge"), ("clean", "package_at_door")]
OOD = ["coffee_spill", "white_mailer"]


def render(cond, fam, seed, det, tag):
    s = make_sample(fam, seed)
    img = perturb(s.image, cond, np.random.default_rng(seed + 1))
    res = det.analyze(img)
    pred = res.primary.label if res.primary else "none"
    ann = res.annotated_bgr if res.annotated_bgr is not None else img
    ann = cv2.resize(ann, (640, 480))
    bar = np.zeros((40, 640, 3), np.uint8)
    cv2.putText(bar, f"{fam} [{cond}] expected={s.expected_label} predicted={pred}", (8, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    out = OUT / f"{tag}.jpg"
    cv2.imwrite(str(out), np.vstack([bar, ann]), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(out.name, seed, s.expected_label, "->", pred)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    det = AnomalyDetector()
    rows = list(csv.DictReader(open(ROOT / "docs/eval/rows.csv")))
    for cond, fam in WANT:
        miss = [r for r in rows if r["condition"] == cond and r["family"] == fam and r["pred_label"] != r["expected_label"]]
        if miss:
            render(cond, fam, int(miss[0]["seed"]), det, f"{fam}_{cond}_miss")
    for fam in OOD:
        r = [x for x in rows if x["family"] == fam]
        render("clean", fam, int(r[0]["seed"]), det, f"ood_{fam}")


if __name__ == "__main__":
    main()
