# ExitRadar — Acquisition Opportunity Engine

> **SaaSquatch answers “Which companies exist?”**  
> **ExitRadar answers “Which acquisition opportunities are forming, why now, who to approach, and what to do next?”**

ExitRadar is a lead-gen quality play for searchers and acquisition entrepreneurs. Instead of dumping thousands of scraped leads, it ranks **thesis-specific opportunities** with evidence, seller-readiness (observable conditions, not P(sale)), timing, access, competition proxies, and a concrete **next-best-action**.

Built for the Caprae / SaaSquatch-style assessment: business prioritization, explainable scoring, ethical discovery, and a polished searcher UX.

## Product loop

```text
FIND → UNDERSTAND → DETECT → TIME → PRIORITIZE → ACT → LEARN
```

1. Write an **acquisition thesis** (NL → structured criteria).
2. Run **discovery** (Google Places + robots-aware web fetch).
3. **Resolve** duplicates into canonical companies.
4. Collect **evidence** → typed **signals** (+ signal events over time).
5. Score **seller readiness** (thesis-independent) and **opportunity** (thesis-specific).
6. Emit **next-best-action**, optional outreach / deal brief, pipeline + activities.
7. Pack a **Weekly Book of Work** (capacity, substitute clusters, research ROI, window expiry).
8. Export ranked CSV for CRM workflows.

## Stack

| Layer | Technology |
|---|---|
| Web | React 18, Vite, Tailwind, TanStack Query, React Router |
| API | Python 3.12, FastAPI, Pydantic v2 |
| Workers | RQ + Redis (inline fallback when Redis is down) |
| DB | PostgreSQL via Supabase (schema in `infra/supabase/migrations`). `DEMO_MODE=true` uses an in-memory store; `DEMO_MODE=false` uses Postgres. |
| Cache / queues | Redis |
| LLM | OpenAI, Anthropic, or **Groq** behind `workers/llm/client.py` (`LLM_PROVIDER`) |
| Discovery | Google Places API + robots.txt-aware web adapter |
| Intended prod host | Vercel (SPA) + Cloud Run (API/workers) + Supabase + Upstash Redis |

See [ARCHITECTURE.md](ARCHITECTURE.md) and [docs/ExitRadar_ERD.png](docs/ExitRadar_ERD.png) for the full design.

## Quick start — Docker (recommended)

```bash
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---------|-----|
| **Web** | http://localhost:8080 |
| **API docs** | http://localhost:8000/docs |
| **Health** | http://localhost:8000/health |

Stack: Redis + FastAPI + RQ worker + nginx (built SPA). Seeded HVAC opportunities load immediately; API keys optional.

Hot-reload (Vite + API reload):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
# UI → http://localhost:5173
```

Full deploy guide (Cloud Run, Vercel, Supabase): **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**

### Local without Docker

```bash
cp .env.example .env
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r apps/api/requirements.txt
export PYTHONPATH=$PWD
uvicorn apps.api.app.main:app --reload --port 8000
# other terminal:
cd apps/web && npm install && npm run dev
```

Open http://localhost:5173.

Without Redis, search jobs run **inline** (sync).

### Optional: live Places + LLM

Set in `.env`:

- `GOOGLE_PLACES_API_KEY`
- `LLM_PROVIDER=groq` with `GROQ_API_KEY` (recommended), or `openai` / `anthropic` with the matching key
- `LLM_MODEL` — e.g. `openai/gpt-oss-120b` (Groq), `gpt-4o-mini` (OpenAI)
- Supabase vars if using hosted Postgres/Auth instead of the demo store (`DEMO_MODE=false`)

Apply SQL in the Supabase SQL editor:

1. `infra/supabase/migrations/001_initial_erd.sql`
2. `infra/supabase/migrations/002_book_of_work.sql` (cadence + weekly plans)
3. `infra/supabase/migrations/003_export_payload.sql`

Then seed HVAC demo data:

```bash
PYTHONPATH=. python scripts/seed_supabase.py
```

## Weekly Book of Work

Radar’s default screen is a **capacity-aware weekly queue**, not a raw score list:

- Closing contact windows first (`expires_at` on recommendations)
- At most one outreach target per substitute metro/industry cluster
- Research slots ranked by expected score/confidence lift per hour
- Complete / Skip actions write activities and can promote a substitute
- Workspace cadence: max outreach + research slots (Thesis page)

Policy version: `bow-v1` in `workers/intelligence/book_of_work.py`.

## API surface (`/api/v1`)

- Workspaces / command center / **cadence**
- Theses CRUD (+ NL parse)
- Search jobs + companies
- Company evidence, signals, timeline, opportunity detail
- Recommendations, outreach, pipeline, activities, deal brief
- **Book of Work** generate / complete / skip
- Exports (JSON / CSV)

Interactive docs: http://localhost:8000/docs

## Demo notebook

See [notebooks/demo_walkthrough.ipynb](notebooks/demo_walkthrough.ipynb) for an API walkthrough.

## Ethical discovery

- `robots.txt` checked before web fetches; denials logged in `compliance_log`
- Per-domain rate limits; CAPTCHA / 403 quarantined (never bypassed)
- Raw payloads append-only with content hashes
- LLM never writes canonical company facts without evidence IDs

## Scoring (deterministic)

```text
SellerReadiness = 0.25 ExitWindow + 0.25 SuccessionVacuum
                + 0.20 DigitalDecay + 0.15 Stagnation + 0.15 RecentChange

OpportunityScore = 0.30 ThesisFit + 0.25 SellerReadiness
                 + 0.20 Timing + 0.15 Access + 0.10 CompetitionAdvantage
```

Every score is versioned; history is not overwritten. UI always shows **why now**, **counter-signals**, and **missing data**.

## Evaluation mapping

| Criterion | How ExitRadar addresses it |
|---|---|
| Business use case | Thesis-fit ranking, seller readiness ≠ spam list, NBA + pipeline for searcher workflow |
| UX/UI | Command Center → table → evidence company page; export; guided thesis |
| Technicality | Multi-source discovery, dedup, enrichment-lite, signal extractors, ethical crawl |
| Design | Dense searcher aesthetic, action color semantics (emerald / amber / muted) |
| Other | Compliance log, explainability, outcome capture hooks, notebook + architecture docs |

## Production deployment

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for the full path:

1. **Supabase** — create project, run migration, Auth + JWT.
2. **Cloud Run** — `apps/api/Dockerfile` → `exitradar-api` + `exitradar-worker` (`./infra/cloudrun/deploy.sh`).
3. **Vercel** — `apps/web` SPA; set `VITE_API_BASE_URL` to the Cloud Run URL.
4. **Redis** — Upstash or Memorystore for RQ (optional; inline fallback exists).
5. **CI** — `.github/workflows/ci.yml` (lint/test/build).

## Video walkthrough outline (90–120s)

See [docs/VIDEO_SCRIPT.md](docs/VIDEO_SCRIPT.md).

## License

MIT — for assessment submission. Respect third-party API Terms of Service.
