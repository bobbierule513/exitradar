# ExitRadar — Deployment Guide

This document covers:

1. **Local Docker** (recommended for demos)
2. **Production path** from [ARCHITECTURE.md](ARCHITECTURE.md) §22: Vercel + Cloud Run + Supabase + Redis

---

## 1. Local Docker (full stack)

### Prerequisites

- Docker Desktop / Engine 24+
- Docker Compose v2+
- Copy env file:

```bash
cp .env.example .env
```

API keys are optional. Without them, Places and LLM use demo fallbacks; the in-memory store seeds HVAC opportunities.

### Start (production-like containers)

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| **Web (nginx SPA)** | http://localhost:8080 |
| **API** | http://localhost:8000 |
| **API docs** | http://localhost:8000/docs |
| **Health** | http://localhost:8000/health |
| **Redis** | localhost:6379 |

Containers:

| Name | Image role |
|------|------------|
| `redis` | Queue / cache for RQ |
| `api` | FastAPI (`uvicorn`) |
| `worker` | RQ worker (`python -m workers.runner`) |
| `web` | Multi-stage Vite build → nginx |

Stop:

```bash
docker compose down
```

### Hot-reload development

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

- Web: http://localhost:5173 (Vite)
- API: http://localhost:8000 with `--reload` + bind mounts

### Useful commands

```bash
# Logs
docker compose logs -f api worker web

# Rebuild one service
docker compose up --build -d api

# Shell into API
docker compose exec api bash

# Run tests inside API image
docker compose run --rm api pytest apps/api/tests -q
```

### CORS note

Compose sets `CORS_ORIGINS` to include `http://localhost:8080` and Vite ports. The browser calls `VITE_API_BASE_URL` (default `http://localhost:8000`). Nginx also proxies `/api/` and `/health` to the API if you later build with an empty base URL for same-origin requests.

---

## 2. Production architecture (target)

From architecture:

| Layer | Technology |
|-------|------------|
| Web | **Vercel** (static SPA) |
| API | **Cloud Run** (container from `apps/api/Dockerfile`) |
| Workers | **Cloud Run** (same image, command `python -m workers.runner`) |
| DB / Auth / Storage | **Supabase** (Postgres + Auth + Storage) |
| Queue / cache | **Upstash Redis** or Memorystore |
| Secrets | Cloud Run / Vercel env vars (never commit `.env`) |
| CI | GitHub Actions |

```text
Browser → Vercel (SPA)
              ↓ HTTPS
         Cloud Run API  ←→  Supabase Postgres
              ↓
         Redis (RQ) → Cloud Run Worker → Places / LLM / web fetch
```

---

## 3. Supabase setup

1. Create a project at [supabase.com](https://supabase.com).
2. Open **SQL Editor** and run, in order:

   [`infra/supabase/migrations/001_initial_erd.sql`](infra/supabase/migrations/001_initial_erd.sql)  
   [`infra/supabase/migrations/002_book_of_work.sql`](infra/supabase/migrations/002_book_of_work.sql)  
   [`infra/supabase/migrations/003_export_payload.sql`](infra/supabase/migrations/003_export_payload.sql)

3. Copy from Project Settings → API:

   - Project URL → `SUPABASE_URL` / `VITE_SUPABASE_URL`
   - `anon` key → `VITE_SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_ROLE_KEY` (**backend only**)
   - JWT secret → `SUPABASE_JWT_SECRET`
   - Database connection string → `DATABASE_URL` (URL-encode `@` in the password as `%40`)

4. Enable Email auth (or your preferred provider) under Authentication.

5. Set `DEMO_MODE=false` and seed HVAC demo data:

   ```bash
   PYTHONPATH=. python scripts/seed_supabase.py
   ```

If a credential was exposed, rotate it before deploy — see [SECRETS.md](SECRETS.md).

---

## 4. Deploy API + worker (Google Cloud Run)

### One-time GCP setup

```bash
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

# Artifact Registry
gcloud artifacts repositories create exitradar \
  --repository-format=docker \
  --location=us-central1
```

### Build & push image

```bash
export REGION=us-central1
export PROJECT=$(gcloud config get-value project)
export IMAGE=$REGION-docker.pkg.dev/$PROJECT/exitradar/api:latest

docker build -f apps/api/Dockerfile -t $IMAGE .
docker push $IMAGE
```

Or Cloud Build:

```bash
gcloud builds submit --tag $IMAGE -f apps/api/Dockerfile .
```

(See also [`infra/cloudrun/`](infra/cloudrun/) for helper scripts.)

### Deploy API service

```bash
gcloud run deploy exitradar-api \
  --image $IMAGE \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5 \
  --set-env-vars "ENVIRONMENT=production,DEMO_MODE=false,CORS_ORIGINS=https://YOUR_VERCEL_DOMAIN,REDIS_URL=YOUR_REDIS_URL,LLM_PROVIDER=openai" \
  --set-secrets "OPENAI_API_KEY=openai-key:latest,GOOGLE_PLACES_API_KEY=places-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_SERVICE_ROLE_KEY=supabase-service:latest,SUPABASE_JWT_SECRET=supabase-jwt:latest"
```

Note the Cloud Run URL, e.g. `https://exitradar-api-xxxxx.run.app`.

### Deploy worker service

Same image, different command (no public HTTP required):

```bash
gcloud run deploy exitradar-worker \
  --image $IMAGE \
  --region $REGION \
  --platform managed \
  --no-allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 3 \
  --command python \
  --args "-m,workers.runner" \
  --set-env-vars "ENVIRONMENT=production,REDIS_URL=YOUR_REDIS_URL,DEMO_MODE=false" \
  --set-secrets "OPENAI_API_KEY=openai-key:latest,GOOGLE_PLACES_API_KEY=places-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_SERVICE_ROLE_KEY=supabase-service:latest"
```

> RQ workers need a long-running process. Prefer Cloud Run **CPU always allocated** / min instances ≥ 1, or run the worker on a small GCE VM / Cloud Run jobs pattern. For assessment demos, Docker Compose worker is simpler.

### Redis options

- **Upstash Redis** (serverless, TLS URL) — set `REDIS_URL=rediss://...`
- **Memorystore** — VPC connector required for Cloud Run

Without Redis, the API falls back to **inline** job execution (still works for demos).

---

## 5. Deploy web (Vercel)

```bash
cd apps/web
npx vercel
```

Or connect the GitHub repo in the Vercel dashboard:

| Setting | Value |
|---------|-------|
| Root directory | `apps/web` |
| Framework | Vite |
| Build command | `npm run build` |
| Output | `dist` |

Environment variables:

| Name | Value |
|------|-------|
| `VITE_API_BASE_URL` | `https://exitradar-api-xxxxx.run.app` |
| `VITE_SUPABASE_URL` | your Supabase URL |
| `VITE_SUPABASE_ANON_KEY` | anon key |

SPA rewrites are in [`infra/vercel.json`](infra/vercel.json) — copy to `apps/web/vercel.json` or set in the Vercel project:

```json
{ "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
```

After deploy, update Cloud Run `CORS_ORIGINS` to the Vercel domain.

---

## 6. Secrets checklist (never commit)

| Secret | Where |
|--------|-------|
| `GOOGLE_PLACES_API_KEY` | Cloud Run |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Cloud Run |
| `SUPABASE_SERVICE_ROLE_KEY` | Cloud Run only |
| `SUPABASE_JWT_SECRET` | Cloud Run |
| `VITE_SUPABASE_ANON_KEY` | Vercel (public by design) |
| `REDIS_URL` | Cloud Run |

---

## 7. CI/CD

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on push/PR:

- Python: install deps + pytest
- Web: `npm install` + `npm run build`

Optional next step: add a `deploy` job that builds/pushes the API image to Artifact Registry on `main`.

---

## 8. Smoke test after deploy

```bash
curl -s https://YOUR_API/health
# {"status":"ok","service":"exitradar-api",...}

curl -s -H "X-Demo-User: 00000000-0000-4000-8000-000000000001" \
  "https://YOUR_API/api/v1/workspaces"
```

Open the Vercel URL → Radar should load opportunities (demo store or Supabase, depending on config).

---

## 9. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Web loads, API errors / CORS | Add the web origin to `CORS_ORIGINS` |
| Charts empty / network error | Check `VITE_API_BASE_URL` matches the reachable API |
| Worker idle | Confirm Redis URL and that worker container/process is running |
| Places returns same 5 companies | Set `GOOGLE_PLACES_API_KEY` |
| Outreach is template text | Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` |
| Data resets on API restart | Expected in `DEMO_MODE=true` / DemoStore — set `DEMO_MODE=false` and run `scripts/seed_supabase.py` |
