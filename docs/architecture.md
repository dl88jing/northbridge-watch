# Architecture — Northbridge Watch

```
┌─────────────────────────────────────────────────────────────────┐
│  Sources: fixture video / webcam / demo scene images            │
└──────────────────────────────┬──────────────────────────────────┘
                               │ frames
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  OpenCV 5 perception (AnomalyDetector)                          │
│  HSV · morphology   · contours · Canny · annotated overlay    │
│  labels: package | spill | empty_fridge | calm                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ structured DetectionResult
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  PolicyEngine (quiet agent)                                     │
│  severity · confidence · multi-object · quiet hours             │
│  → noop | auto_log | notify | human_required                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │ ActionDecision changes next step
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Act                                                             │
│  Local JSONL store  OR  API GW → Lambda → S3 (+ SNS notify)     │
│  Escalations pause further automation until human ack            │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Judge UI (Vercel) — scene picker, annotated frame, agent trace │
└─────────────────────────────────────────────────────────────────┘
```

## Agentic Vision loop

1. **Perceive** — OpenCV 5 analyzes the frame; evidence is not a caption, it is structured detections with confidence and bbox.
2. **Decide** — Policy maps evidence → action kind. Multi-package or spill raises `human_required`; calm → `noop`; sparse fridge at night → deferred `auto_log`.
3. **Act** — Persist event, notify Avery/Morgan, or escalate and await ack. The visual result **changes** which branch runs.

## Competition path

- Featured path: **Agentic Vision** (primary). COOL/Graviton optional stretch documented in `aws-deploy.md`.
