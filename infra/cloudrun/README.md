# Cloud Run / Artifact Registry helpers
#
# Full guide: docs/DEPLOYMENT.md
#
# Quick path:
#   chmod +x infra/cloudrun/deploy.sh
#   export GCP_PROJECT=... CORS_ORIGINS=https://....vercel.app REDIS_URL=...
#   ./infra/cloudrun/deploy.sh
#
# Manual:
#   docker build -f apps/api/Dockerfile -t exitradar-api .
#   gcloud run deploy exitradar-api --image ... --port 8000
#   gcloud run deploy exitradar-worker --image ... --command python --args "-m,workers.runner"
