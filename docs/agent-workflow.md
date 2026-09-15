# Agentic Vision workflow (award evidence)

```
frame → OpenCV5 tools → DetectionResult
                              │
                              ▼
                     PolicyEngine.decide()
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
           noop          auto_log         notify / human_required
                              │               │
                              ▼               ▼
                         persist S3/JSONL   SNS + await_human
```

## Trace requirement

Each `AgentTrace` records:

- `perception` — OpenCV labels, confidence, metrics, version
- `decision` — action kind + reason (evidence-dependent)
- `actions_taken` — concrete side effects

Demo: spill always escalates; calm never notifies; busy porch → `human_required`. Same image always yields the same branch — vision **controls** the plan.
