"""Run the evaluation and write docs/eval/results.json + results.md.

Usage:  python -m northbridge_watch.eval.run_eval [--n 40]
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from northbridge_watch.agent.policy import PolicyEngine
from northbridge_watch.eval.synth import CONDITIONS, FAMILIES, OOD_FAMILIES, make_sample, perturb
from northbridge_watch.vision.detector import AnomalyDetector

DAYTIME = datetime(2026, 9, 15, 15, 0, 0, tzinfo=timezone.utc)
LABELS = ["package", "spill", "empty_fridge"]
ROOT = Path(__file__).resolve().parents[2]


def _prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * p * r / (p + r) if p and r else (0.0 if p is not None and r is not None else None)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f}


def evaluate(families: dict, conditions: list[str], n: int, seed0: int = 1000) -> dict:
    det = AnomalyDetector()
    pol = PolicyEngine()
    rows = []
    for cond in conditions:
        for fam in families:
            for i in range(n):
                seed = seed0 + i * 97 + hash_stable(fam)
                s = make_sample(fam, seed)
                img = perturb(s.image, cond, np.random.default_rng(seed + 1))
                t0 = time.perf_counter()
                res = det.analyze(img)
                d = res.to_dict()
                dec = pol.decide(d, now=DAYTIME)
                dt = (time.perf_counter() - t0) * 1000
                pred = d["primary"]["label"] if d["primary"] else "none"
                n_pred_pk = sum(1 for x in d["detections"] if x["label"] == "package")
                rows.append({
                    "condition": cond, "family": fam, "seed": seed,
                    "expected_label": s.expected_label, "pred_label": pred,
                    "expected_action": s.expected_action, "pred_action": dec.action.value,
                    "n_packages": s.n_packages, "n_pred_packages": n_pred_pk,
                    "ms": dt,
                })
    return summarize(rows, conditions, list(families)), rows


def hash_stable(s: str) -> int:
    import zlib
    return zlib.crc32(s.encode()) % 10_000


def summarize(rows, conditions, families) -> dict:
    out: dict = {"by_condition": {}, "by_family": {}}
    for cond in conditions:
        rs = [r for r in rows if r["condition"] == cond]
        per_label = {}
        for lab in LABELS:
            tp = sum(1 for r in rs if r["pred_label"] == lab and r["expected_label"] == lab)
            fp = sum(1 for r in rs if r["pred_label"] == lab and r["expected_label"] != lab)
            fn = sum(1 for r in rs if r["pred_label"] != lab and r["expected_label"] == lab)
            if tp + fp + fn:
                per_label[lab] = _prf(tp, fp, fn)
        ms = [r["ms"] for r in rs]
        busy = [r for r in rs if r["family"] == "busy_porch"]
        out["by_condition"][cond] = {
            "n": len(rs),
            "label_accuracy": sum(r["pred_label"] == r["expected_label"] for r in rs) / len(rs),
            "action_accuracy": sum(r["pred_action"] == r["expected_action"] for r in rs) / len(rs),
            "per_label": per_label,
            "busy_count_exact": (sum(r["n_pred_packages"] == r["n_packages"] for r in busy) / len(busy)) if busy else None,
            "latency_ms_p50": statistics.median(ms),
            "latency_ms_p95": float(np.percentile(ms, 95)),
        }
        for fam in families:
            fr = [r for r in rs if r["family"] == fam]
            out["by_family"].setdefault(fam, {})[cond] = {
                "n": len(fr),
                "label_accuracy": sum(r["pred_label"] == r["expected_label"] for r in fr) / len(fr),
                "action_accuracy": sum(r["pred_action"] == r["expected_action"] for r in fr) / len(fr),
                "confusions": _confusions(fr),
            }
    return out


def _confusions(fr):
    c: dict[str, int] = {}
    for r in fr:
        if r["pred_label"] != r["expected_label"]:
            c[r["pred_label"]] = c.get(r["pred_label"], 0) + 1
    return c


def canonical_fixtures() -> list[dict]:
    from northbridge_watch.vision.scenes import SCENE_SPECS, generate_scene, list_scene_kinds
    det, pol = AnomalyDetector(), PolicyEngine()
    out = []
    for k in list_scene_kinds():
        img = generate_scene(k)
        ts = []
        for _ in range(50):
            t0 = time.perf_counter(); res = det.analyze(img); ts.append((time.perf_counter() - t0) * 1000)
        d = res.to_dict(); dec = pol.decide(d, now=DAYTIME)
        out.append({"scene": k.value, "expected": SCENE_SPECS[k].expected_label,
                    "pred": d["primary"]["label"] if d["primary"] else "none",
                    "conf": d["primary"]["confidence"] if d["primary"] else 0.0,
                    "n_det": len(d["detections"]), "action": dec.action.value,
                    "ms_p50": statistics.median(ts)})
    return out


def fmt(x):
    return "n/a" if x is None else f"{x:.3f}"


def to_markdown(res: dict) -> str:
    L = [f"# Evaluation results\n", f"Generated {res['meta']['generated_utc']} UTC on `{res['meta']['machine']}`, "
         f"OpenCV {res['meta']['opencv']}, Python {res['meta']['python']}, n={res['meta']['n_per_family']} per family per condition, "
         f"split={res['meta'].get('split')} (seed0={res['meta'].get('seed0')}).\n",
         "## Canonical demo fixtures (5 images)\n", "| Scene | Expected | Predicted | Conf | #det | Action | p50 ms |", "|---|---|---|---|---|---|---|"]
    for r in res["canonical"]:
        L.append(f"| {r['scene']} | {r['expected']} | {r['pred']} | {r['conf']:.2f} | {r['n_det']} | {r['action']} | {r['ms_p50']:.2f} |")
    for key, title in (("in_domain", "In-domain randomized scenes (7 families)"), ("ood", "Out-of-domain families (clean condition)")):
        block = res[key]
        L += [f"\n## {title}\n", "| Condition | N | Label acc | Action acc | Package P/R | Spill P/R | Empty-fridge P/R | Busy count exact | p50 ms | p95 ms |", "|---|---|---|---|---|---|---|---|---|---|"]
        for cond, m in block["by_condition"].items():
            pl = m["per_label"]
            def pr(l):
                return f"{fmt(pl[l]['precision'])} / {fmt(pl[l]['recall'])}" if l in pl else "n/a"
            L.append(f"| {cond} | {m['n']} | {m['label_accuracy']:.3f} | {m['action_accuracy']:.3f} | {pr('package')} | {pr('spill')} | {pr('empty_fridge')} | {fmt(m['busy_count_exact'])} | {m['latency_ms_p50']:.2f} | {m['latency_ms_p95']:.2f} |")
        L += ["\n### Per-family label accuracy\n", "| Family | " + " | ".join(block["by_condition"]) + " |", "|---|" + "---|" * len(block["by_condition"])]
        for fam, cm in block["by_family"].items():
            cells = []
            for cond in block["by_condition"]:
                c = cm[cond]
                conf = ", ".join(f"{k}:{v}" for k, v in c["confusions"].items())
                cells.append(f"{c['label_accuracy']:.2f}" + (f" ({conf})" if conf else ""))
            L.append(f"| {fam} | " + " | ".join(cells) + " |")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed0", type=int, default=50000, help="1000 = dev split used while tuning; 50000 = held-out test split")
    ap.add_argument("--out", default=str(ROOT / "docs" / "eval"))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ind, ind_rows = evaluate(FAMILIES, CONDITIONS, a.n, a.seed0)
    ood, ood_rows = evaluate(OOD_FAMILIES, ["clean"], a.n, a.seed0)
    res = {
        "meta": {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                 "opencv": cv2.__version__, "python": platform.python_version(),
                 "machine": f"{platform.system()} {platform.machine()}, {cv2.getNumberOfCPUs()} CPUs",
                 "n_per_family": a.n, "seed0": a.seed0, "split": "dev" if a.seed0 == 1000 else "test", "policy_clock": DAYTIME.isoformat()},
        "canonical": canonical_fixtures(), "in_domain": ind, "ood": ood,
    }
    (out / "results.json").write_text(json.dumps(res, indent=2))
    (out / "results.md").write_text(to_markdown(res))
    with (out / "rows.csv").open("w") as f:
        keys = list(ind_rows[0])
        f.write(",".join(keys) + "\n")
        for r in ind_rows + ood_rows:
            f.write(",".join(str(round(r[k], 3) if isinstance(r[k], float) else r[k]) for k in keys) + "\n")
    print(to_markdown(res))


if __name__ == "__main__":
    main()
