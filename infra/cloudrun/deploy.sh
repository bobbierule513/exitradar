#!/usr/bin/env bash
# Build and push ExitRadar API image to Artifact Registry, then deploy Cloud Run services.
# Usage:
#   export GCP_PROJECT=your-project
#   export REGION=us-central1
#   export CORS_ORIGINS=https://your-app.vercel.app
#   export REDIS_URL=rediss://...
#   ./infra/cloudrun/deploy.sh

set -euo pipefail

PROJECT="${GCP_PROJECT:-$(gcloud config get-value project)}"
REGION="${REGION:-us-central1}"
REPO="${ARTIFACT_REPO:-exitradar}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/api:latest"

echo "==> Project: $PROJECT  Region: $REGION"
echo "==> Image:   $IMAGE"

gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --project "$PROJECT"

if ! gcloud artifacts repositories describe "$REPO" --location="$REGION" --project="$PROJECT" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --project="$PROJECT"
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "==> Building image"
docker build -f apps/api/Dockerfile -t "$IMAGE" .

echo "==> Pushing image"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
docker push "$IMAGE"

ENV_VARS="ENVIRONMENT=production,DEMO_MODE=${DEMO_MODE:-true}"
if [[ -n "${CORS_ORIGINS:-}" ]]; then
  ENV_VARS="${ENV_VARS},CORS_ORIGINS=${CORS_ORIGINS}"
fi
if [[ -n "${REDIS_URL:-}" ]]; then
  ENV_VARS="${ENV_VARS},REDIS_URL=${REDIS_URL}"
fi

echo "==> Deploying exitradar-api"
gcloud run deploy exitradar-api \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --memory 1Gi \
  --cpu 1 \
  --set-env-vars "$ENV_VARS" \
  --project "$PROJECT"

echo "==> Deploying exitradar-worker"
gcloud run deploy exitradar-worker \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --no-allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 1 \
  --command python \
  --args "-m,workers.runner" \
  --set-env-vars "$ENV_VARS" \
  --project "$PROJECT"

echo "==> Done. Set secrets (Places, LLM, Supabase) in Cloud Run console or via --set-secrets."
gcloud run services describe exitradar-api --region "$REGION" --format='value(status.url)'
