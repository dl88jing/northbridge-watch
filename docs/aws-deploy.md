# AWS deployment path

> **Status (2026-10-25): not deployed.** No AWS credentials were available in the build environment. Everything below is ready to run; `make deploy-aws` performs the full deploy + Vercel wiring.

## Meaningful AWS component (required)

| Service | Role |
|---------|------|
| **API Gateway** | HTTPS ingest for perception/decision payloads |
| **Lambda (arm64)** | Validate, persist, optional SNS fan-out |
| **S3** | Durable event JSON (+ optional annotated frames) |
| **SNS** | Quiet notify / human_required alerts to Avery & Morgan |

SAM template: [`aws/template.yaml`](../aws/template.yaml).

### Deploy (when AWS credentials available)

One command: `make deploy-aws` (runs `scripts/deploy_aws.sh --wire-vercel`). Manual equivalent:

```bash
cd aws
sam build
sam deploy --guided \
  --stack-name northbridge-watch \
  --capabilities CAPABILITY_IAM
```

Set `NW_S3_BUCKET` and `NW_SNS_TOPIC_ARN` on the function (template wires these).

### Edge vs cloud split

- **Edge / laptop / Vercel demo fixtures:** OpenCV 5 runs in Python (`AnomalyDetector`).
- **Cloud ingest:** Lambda receives structured perception JSON (and optionally frame bytes to S3).
- **Stretch — COOL on Graviton:** run the same OpenCV workload on an `m7g`/`c7g` instance or Lambda container with [Cloud-Optimized OpenCV (COOL)](https://aws.amazon.com/marketplace/seller-profile?id=seller-q3au5rsqt2mq6) and publish latency vs `opencv-python-headless` baseline.

### Offline judges

No AWS keys needed: `LocalEventStore` writes `fixtures/events/*.jsonl` with the **same payload schema** as the S3 object body.
