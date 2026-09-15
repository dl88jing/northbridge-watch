# Northbridge Watch

**OpenCV AI Competition 2026 (powered by AWS)** — Agentic Vision path.

> Quiet home perception for the fictional **Northbridge** household (**Avery & Morgan**): OpenCV 5 watches porch/kitchen demo scenes, then an agent policy chooses **notify** vs **auto-log** vs **human-required**. Vision evidence changes the next action.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![OpenCV](https://img.shields.io/badge/OpenCV-5.0-green.svg)](https://opencv.org/)
[![AWS](https://img.shields.io/badge/AWS-Lambda%20%2B%20S3%20%2B%20API%20GW-orange.svg)](docs/aws-deploy.md)

**Hackathon:** [opencv26.devpost.com](https://opencv26.devpost.com/) · **Grant form:** [Jotform 262145877145059](https://form.jotform.com/262145877145059)

---

## Live demo

**Judge UI (Vercel):** [https://northbridge-watch.vercel.app](https://northbridge-watch.vercel.app)

Static fixture traces ship in `web/public/demo/` so judges can explore without a GPU or webcam. Full OpenCV 5 loop: `./demo.sh`.

---

## Why this fits the brief

| Requirement | Northbridge Watch |
|-------------|-------------------|
| OpenCV 5 substantive | HSV/Lab, morphology, contours, Canny, annotated overlays — not a wrapper around a black-box captioner |
| Meaningful AWS | API Gateway → Lambda (arm64) → S3 event store + SNS alerts ([`aws/template.yaml`](aws/template.yaml)) |
| Agentic Vision | Perception → PolicyEngine → act (notify / auto-log / escalate). Spill always escalates; calm never notifies |
| Judgeable offline | `./demo.sh` — no AWS keys |
| Live web endpoint | Vercel scene explorer with agent traces |

---

## Judge quickstart (~60 seconds)

```bash
git clone https://github.com/dl88jing/northbridge-watch.git
cd northbridge-watch
./demo.sh
```

Expected highlights:

| Scene | Perception | Action |
|-------|------------|--------|
| `calm_porch` | none | `noop` |
| `package_at_door` | package | `notify` or `auto_log` |
| `busy_porch` | multi-package | `human_required` |
| `floor_spill` | spill | `human_required` |
| `empty_fridge` | empty_fridge | `notify` / quiet `auto_log` |

### API + web (local)

```bash
./demo.sh serve   # http://127.0.0.1:8787/api/health
./demo.sh web     # Vite UI → proxies /api when configured
```

---

## Architecture

```
fixture / webcam frame
        │
        ▼
 OpenCV 5 AnomalyDetector  ──► DetectionResult (label, conf, bbox)
        │
        ▼
 PolicyEngine (quiet hours, severity, multi-object)
        │
        ├── noop
        ├── auto_log  ──► Local JSONL or Lambda→S3
        ├── notify    ──► SNS / push mock → Avery or Morgan
        └── human_required ──► escalate + await ack
        │
        ▼
 Vercel judge UI (annotated frame + agent trace)
```

Details: [`docs/architecture.md`](docs/architecture.md) · Agent evidence: [`docs/agent-workflow.md`](docs/agent-workflow.md) · AWS: [`docs/aws-deploy.md`](docs/aws-deploy.md)

---

## OpenCV 5 usage

Pinned: `opencv-python-headless==5.0.0.93`

- **Package-at-door:** HSV brown mask → morph close/open → contours → rectangularity score  
- **Spill:** HSV saturation + Lab `a` channel → irregular blob solidity  
- **Empty fridge:** bright interior + low Canny edge density on shelf ROI  
- **Evidence:** every run stamps `cv2.__version__` and writes an annotated JPEG

Implementation: [`northbridge_watch/vision/detector.py`](northbridge_watch/vision/detector.py)

---

## AWS usage

| Piece | Purpose |
|-------|---------|
| API Gateway `POST /ingest` | Accept perception/decision payloads |
| Lambda arm64 | Persist + optional SNS |
| S3 | Durable events (`events/{id}.json`) |
| SNS | Quiet alerts for notify / human_required |

Offline parity: `LocalEventStore` uses the **same JSON schema**.  
Deploy guide: [`docs/aws-deploy.md`](docs/aws-deploy.md)

---

## Repository layout

```
northbridge_watch/     Python package (vision, agent, aws, api)
aws/                   SAM template + Lambda entry
docs/                  Architecture, AWS, agent workflow, grant draft
fixtures/              Generated scenes, annotated frames, events
scripts/               Fixture generator + CLI demo
web/                   Vercel judge UI (static demo catalog + API client)
```

---

## Cloud compute grant

Proposal draft: [`docs/grant-proposal-draft.md`](docs/grant-proposal-draft.md)  
**Form:** https://form.jotform.com/262145877145059  

Grant is optional for prize eligibility; still useful for Lambda/Graviton/COOL experiments.

---

## Responsible use

Demo scenes are synthetic. Real deployments must obtain consent for cameras, minimize retention, default to on-device perception, and keep **human_required** for safety hazards (spills). No biometric identification.

---

## License

Apache-2.0 — see [LICENSE](LICENSE).

Team: **Northbridge** · Household: **Avery & Morgan**
