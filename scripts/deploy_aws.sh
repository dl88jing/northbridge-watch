#!/usr/bin/env bash
# Deploy the AWS ingest stack (API Gateway + Lambda arm64 + S3 + SNS) with SAM,
# then point the live Vercel app at it. Requires AWS credentials in the environment
# (AWS_PROFILE or AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY) and the `sam` CLI.
set -euo pipefail
cd "$(dirname "$0")/.."
REGION="${AWS_REGION:-us-west-2}"
STACK="${NW_STACK:-northbridge-watch}"
command -v sam >/dev/null || { echo "Install AWS SAM CLI: pip install aws-sam-cli"; exit 1; }
aws sts get-caller-identity >/dev/null || { echo "No working AWS credentials"; exit 1; }
sam build -t aws/template.yaml
sam deploy --stack-name "$STACK" --region "$REGION" --capabilities CAPABILITY_IAM \
  --resolve-s3 --no-confirm-changeset --no-fail-on-empty-changeset
URL=$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
echo "ApiUrl: $URL"
curl -fsS "${URL%/}/health" && echo
if [[ "${1:-}" == "--wire-vercel" ]]; then
  # Stored as a Vercel project env var (never committed).
  printf '%s' "${URL%/}" | vercel env add NW_AWS_INGEST_URL production --force
  vercel deploy --prod --yes
fi
