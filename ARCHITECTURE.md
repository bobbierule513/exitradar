# ExitRadar — Final Architecture

> **Acquisition intelligence infrastructure for searchers and acquisition entrepreneurs.**  
> Version: 2.0 · PostgreSQL / Supabase · FastAPI · RQ/Redis · React/Vite

---

## 1. Product thesis

SaaSquatch Leads answers **“Which companies exist?”**

ExitRadar should answer the harder question:

> **“Which acquisition opportunities are forming, why are they interesting now, who should I approach, and what should I do next?”**

The product therefore evolves from a seller-readiness score into an **Acquisition Opportunity Engine**.

### Core loop

```text
FIND → UNDERSTAND → DETECT → TIME → PRIORITIZE → ACT → LEARN
```

The long-term moat is not another scraper or another opaque “seller intent” score. It is the continuously updated combination of:

- acquisition theses
- canonical company entities
- evidence and provenance
- temporal signals and changes
- seller readiness
- strategic fit
- accessibility / relationship context
- competitive pressure
- next-best-action recommendations
- user actions and eventual deal outcomes

This turns ExitRadar into a **decision system**, not a lead list.

---

## 2. System goals

### Primary goals

1. Discover companies from multiple public and licensed sources.
2. Resolve duplicate records into a canonical company entity.
3. Preserve raw source payloads and provenance for auditability and replay.
4. Convert observations into evidence-backed, time-aware signals.
5. Separate **seller readiness** from **thesis-specific opportunity**.
6. Score opportunities deterministically and explain every score.
7. Recommend a concrete next action instead of merely ranking leads.
8. Generate outreach only from verified company/contact/evidence context.
9. Learn from user actions, responses, pipeline movement, and outcomes.
10. Respect source terms, robots rules, rate limits, privacy constraints, and data-retention policies.

### Non-goals

- Predicting with certainty that an owner will sell.
- Automatically bypassing CAPTCHAs, access controls, or anti-bot mechanisms.
- Treating LLM output as authoritative company data.
- Building a full CRM in the first release.

---

## 3. Architecture principles

### 3.1 Evidence before intelligence

The canonical processing contract is:

```text
SOURCE
  ↓
OBSERVATION
  ↓
NORMALIZATION
  ↓
EVIDENCE
  ↓
DETERMINISTIC SIGNAL
  ↓
TEMPORAL CHANGE
  ↓
SCORE
  ↓
LLM INTERPRETATION
  ↓
RECOMMENDATION
```

Never use:

```text
WEB → LLM → “This company looks like a seller.”
```

The LLM can interpret evidence, classify unstructured text, summarize, and draft language. It cannot silently become the source of truth.

### 3.2 Raw data is immutable

`raw_leads` and evidence snapshots are append-only. Normalized entities may change as better evidence arrives, but the original observation remains recoverable.

### 3.3 Scores are versioned

Every score stores the model/ruleset version and the time it was computed. Reweighting a model creates a new score; it does not rewrite history.

### 3.4 Separate company truth from thesis judgment

A company should have one canonical representation. Different acquisition theses can evaluate that same company differently.

```text
Company
  ├── Seller Readiness = thesis-independent
  └── Opportunity Score = thesis-specific
```

### 3.5 Temporal data is first-class

A static score is weak. The system should detect movement:

```text
signal at t0 → signal at t1 → delta → momentum → opportunity window
```

The UI should show **what changed**, not just the latest value.

### 3.6 Confidence is explicit

Every extracted signal and important relationship carries confidence and evidence references. Missing evidence is different from negative evidence.

### 3.7 Recommendations expire

A “contact now” recommendation can become stale. Recommendations therefore have status, priority, creation time, and an expiration time.

---

## 4. High-level system architecture

```text
                                  ┌─────────────────────────┐
                                  │       WORKSPACE         │
                                  │  Users / Members / ICP  │
                                  └────────────┬────────────┘
                                               │
                                               ▼
                                  ┌─────────────────────────┐
                                  │   ACQUISITION THESIS    │
                                  │ strategy + constraints  │
                                  └────────────┬────────────┘
                                               │
                                               ▼
                                  ┌─────────────────────────┐
                                  │    MARKET MAPPING       │
                                  │ segments / whitespace   │
                                  └────────────┬────────────┘
                                               │
                                               ▼
                                  ┌─────────────────────────┐
                                  │     DISCOVERY LAYER     │
                                  │ Maps / Web / APIs / DBs │
                                  └────────────┬────────────┘
                                               │
                                               ▼
                                  ┌─────────────────────────┐
                                  │      RAW LEADS          │
                                  │ immutable source data  │
                                  └────────────┬────────────┘
                                               │
                                               ▼
                                  ┌─────────────────────────┐
                                  │    ENTITY RESOLUTION    │
                                  │ normalize + deduplicate  │
                                  └────────────┬────────────┘
                                               │
                                               ▼
                         ┌──────────────────────────────────────────┐
                         │             CANONICAL GRAPH              │
                         │ Companies · Contacts · Sources           │
                         │ Relationships · Transactions             │
                         └───────────────────┬──────────────────────┘
                                             │
                                             ▼
                         ┌──────────────────────────────────────────┐
                         │          EVIDENCE & SIGNAL LAYER          │
                         │ Evidence → Signals → Signal Events      │
                         └───────────────────┬──────────────────────┘
                                             │
                         ┌───────────────────┴───────────────────┐
                         ▼                                       ▼
              ┌─────────────────────┐                 ┌─────────────────────┐
              │ SELLER READINESS    │                 │   THESIS FIT        │
              │ exit / succession   │                 │ industry / geo /    │
              │ digital / stagnation│                 │ size / strategy     │
              └──────────┬──────────┘                 └──────────┬──────────┘
                         └──────────────────┬────────────────────┘
                                            ▼
                                  ┌─────────────────────────┐
                                  │  DEALABILITY ENGINE     │
                                  │ Fit + Seller + Timing  │
                                  │ Access + Competition   │
                                  └────────────┬────────────┘
                                               │
                                               ▼
                                  ┌─────────────────────────┐
                                  │   OPPORTUNITY GRAPH     │
                                  │ market + relationships  │
                                  └────────────┬────────────┘
                                               │
                                               ▼
                                  ┌─────────────────────────┐
                                  │   DECISION ENGINE       │
                                  │ next-best-action        │
                                  └───────┬─────┬─────┬─────┘
                                          │     │     │
                                ┌─────────┘     │     └──────────┐
                                ▼               ▼                ▼
                           MONITOR          RESEARCH          OUTREACH
                                │               │                │
                                └───────────────┼────────────────┘
                                                ▼
                                  ┌─────────────────────────┐
                                  │      DEAL PIPELINE      │
                                  │ activity / stage / CRM  │
                                  └────────────┬────────────┘
                                               │
                                               ▼
                                  ┌─────────────────────────┐
                                  │       OUTCOMES          │
                                  │ response / pass / deal  │
                                  └────────────┬────────────┘
                                               │
                                               ▼
                                  ┌─────────────────────────┐
                                  │     LEARNING LOOP       │
                                  │ calibration / ranking   │
                                  └─────────────────────────┘
```

---

## 5. Core domain model

### 5.1 Acquisition thesis

An acquisition thesis is the user's strategy, not merely a search filter.

Example:

> “US-based HVAC service businesses, $2–10M revenue, owner-operated, recurring commercial customers, preferably 15+ years old, within 90 minutes of an existing platform.”

Stored as structured criteria plus strategy metadata so the system can evaluate fit deterministically and use AI for interpretation.

### 5.2 Canonical company

`companies` is the canonical entity. Source-specific records never become the canonical truth directly.

A company can have:

- many source records
- many contacts
- many evidence items
- many signals over time
- many thesis-specific opportunity scores
- many relationships to other companies/people
- many pipeline activities

### 5.3 Evidence

`evidence_items` is the provenance layer.

An evidence item should answer:

- where did this fact come from?
- when was it observed?
- what exactly was observed?
- what source produced it?
- can the system reproduce or inspect it later?

Evidence can be a URL/snippet, structured API response, page snapshot, or other permitted source artifact.

### 5.4 Signals

Signals are normalized observations such as:

- owner tenure estimate
- founder/principal identified
- succession indicator
- leadership change
- website freshness
- hiring trend
- review trend
- headcount trend
- business age
- acquisition/comparable transaction nearby
- strategic fit indicator

Signals should be typed, confidence-aware, and time-aware.

### 5.5 Signal events

A `signal_event` records a meaningful change in a signal:

```text
previous_value = 12 open jobs
current_value  = 4 open jobs
delta          = -8
observed_at    = 2026-09-10
```

This enables momentum and opportunity-window calculations.

---

## 6. Intelligence engines

### 6.1 Seller Readiness Engine

Seller readiness is **not** “probability of sale.” It is an explainable composite describing observable conditions associated with a business becoming more likely to consider transition.

Suggested components:

```text
SellerReadiness =
    0.25 × ExitWindow
  + 0.25 × SuccessionVacuum
  + 0.20 × DigitalDecay
  + 0.15 × Stagnation
  + 0.15 × RecentChange
```

The exact weights are configuration, not hard-coded truth. Each component is 0–100 and every component must retain its evidence.

### 6.2 Thesis Fit Engine

Fit is deterministic wherever possible:

- industry
- geography
- revenue/size
- age
- business model
- ownership profile
- strategic constraints

A user can inspect why a company passed or failed each criterion.

### 6.3 Timing Engine

Timing measures whether the opportunity is becoming more actionable now.

Inputs may include:

- accelerating seller-readiness signals
- recent leadership changes
- business deterioration/improvement patterns
- market events
- comparable transactions
- changes in competition
- time since prior outreach

The system should distinguish:

- **ready now**
- **warming up**
- **watch**
- **not actionable**

### 6.4 Access / Relationship Engine

A great company is less useful if there is no credible path to the decision-maker.

Access can incorporate:

- known owner/contact
- verified business email
- direct phone
- warm relationship
- shared network/relationship edge when legally and technically available
- advisor/intermediary connection
- previous outreach history

### 6.5 Competition Engine

Competition measures how crowded the opportunity is, rather than assuming the most “sellable” company is always the best target.

Potential inputs:

- number of known buyers watching the segment
- comparable transaction activity
- advisor/intermediary activity
- overlapping thesis coverage
- market demand signals

The score should remain confidence-aware because competitor data is often incomplete.

### 6.6 Dealability / Opportunity Score

The primary ranking should be thesis-specific:

```text
OpportunityScore =
    0.30 × ThesisFit
  + 0.25 × SellerReadiness
  + 0.20 × Timing
  + 0.15 × Access
  + 0.10 × CompetitionAdvantage
```

This is intentionally not a “probability the company will sell.” It is a **decision-prioritization score**.

Every score response should expose:

- total score
- component scores
- confidence
- positive evidence
- counter-signals
- score version
- “why now?” explanation

### 6.7 Decision / Next-Best-Action Engine

The score is only useful if it changes behavior.

Possible actions:

```text
CONTACT_NOW
RELATIONSHIP_FIRST
RESEARCH_MORE
MONITOR
DEPRIORITIZE
```

Recommendations are generated from structured rules plus optional LLM interpretation. The LLM can explain the decision in natural language, but the action policy remains inspectable.

---

## 7. Opportunity Graph

The relational database acts as the source of truth; a graph representation can be derived from it when graph traversal becomes valuable.

Important edges include:

```text
Company ── employs ──> Contact
Company ── related_to ──> Company
Company ── acquired_by ──> Company
Company ── competed_with ──> Company
Company ── advised_by ──> Contact/Advisor
Company ── comparable_to ──> Company
```

This enables questions such as:

- Who owns companies similar to my best targets?
- Which adjacent market has strong fit but low competitive pressure?
- Which advisors appear repeatedly around relevant transactions?
- Which companies are connected to recent comparable acquisitions?

Do not introduce a dedicated graph database until PostgreSQL queries are demonstrably insufficient. Start with relational edges and add a graph projection later.

---

## 8. Temporal intelligence

The system must preserve history rather than overwrite the current state.

Example:

```text
May      owner tenure: 26 years     website: active       hiring: +3
June     owner tenure: 26 years     website: stale        hiring: 0
July     owner tenure: 27 years     website: stale        hiring: -2
August   leadership change detected website: stale        hiring: -4
September                         → Opportunity Window opens
```

A temporal engine computes:

- delta
- velocity
- acceleration
- persistence
- recency
- signal agreement

The UI should surface the **trajectory** alongside the latest score.

---

## 9. Market mapping and white-space detection

A thesis can be expanded beyond the user's initial keywords.

```text
User thesis
    ↓
Market taxonomy
    ↓
Adjacent segments
    ↓
Company universe
    ↓
Fit × Readiness × Competition
    ↓
White-space opportunities
```

Example:

```text
HVAC
├── Commercial HVAC
├── Refrigeration
├── Building Maintenance
├── Industrial Climate Control
└── Energy Services
```

The system can identify segments where:

- target fit is high
- seller readiness is favorable
- competition appears lower
- sufficient company density exists

AI may propose adjacent segments, but they should be stored as hypotheses until supported by observed data.

---

## 10. Data flow: one company

```text
1. Source adapter discovers a record
2. Raw payload is persisted with content hash
3. Normalizer extracts canonical fields
4. Entity resolver matches or creates company
5. Source provenance is attached to company
6. Evidence collector stores permitted observations
7. Signal extractors create/update typed signals
8. Signal event detector records meaningful changes
9. Seller Readiness Engine computes versioned score
10. Thesis Fit Engine evaluates each relevant thesis
11. Timing / Access / Competition engines evaluate context
12. Opportunity Engine computes versioned Opportunity Score
13. Decision Engine emits recommendation
14. LLM creates optional human-readable deal brief/outreach
15. User acts
16. Activity/outcome is recorded
17. Learning layer uses outcomes for calibration and ranking
```

---

## 11. Data model / ERD

The canonical ERD is available as:

- `docs/ExitRadar_ERD.mmd` — Mermaid source
- `docs/ExitRadar_ERD.svg` — rendered vector diagram
- `docs/ExitRadar_ERD.png` — rendered image

The diagram intentionally keeps the schema relational and avoids premature microservices/graph-database complexity.

### Core entities

| Entity | Responsibility |
|---|---|
| `users` | Supabase-authenticated user profile |
| `workspaces` | tenant boundary |
| `workspace_members` | membership and roles |
| `acquisition_theses` | acquisition strategy + structured criteria |
| `search_jobs` | discovery/enrichment runs |
| `raw_leads` | immutable source payloads |
| `companies` | canonical company entity |
| `company_sources` | source provenance / external IDs |
| `contacts` | decision-makers and business contacts |
| `evidence_items` | immutable evidence/provenance |
| `signals` | current normalized intelligence |
| `signal_events` | temporal changes in signals |
| `seller_readiness_scores` | thesis-independent readiness history |
| `opportunity_scores` | thesis-specific prioritization history |
| `recommendations` | next-best-action decisions |
| `company_relationships` | company-to-company graph edges |
| `transactions` | comparable acquisition/transaction context |
| `outreach_drafts` | evidence-grounded communication drafts |
| `deal_pipeline` | target progression |
| `activities` | user/system actions and outcomes |
| `exports` | generated datasets |
| `compliance_log` | crawl/data-policy audit trail |

---

## 12. Important constraints and indexes

### Uniqueness

- `companies.domain` should be normalized before uniqueness is enforced.
- `company_sources(source, external_id)` should be unique where the source guarantees stable IDs.
- `raw_leads(search_job_id, source, external_id)` should be unique when available.
- `workspace_members(workspace_id, user_id)` must be unique.
- `opportunity_scores(company_id, thesis_id, computed_at)` should preserve historical versions rather than overwrite.

### High-value indexes

```text
companies(domain)
companies(country, state, industry)
company_sources(source, external_id)
contacts(company_id)
signals(company_id, signal_type, last_observed_at)
signal_events(company_id, observed_at)
seller_readiness_scores(company_id, computed_at DESC)
opportunity_scores(thesis_id, opportunity_score DESC)
opportunity_scores(company_id, thesis_id, computed_at DESC)
recommendations(thesis_id, status, priority)
company_relationships(company_id, relationship_type)
activities(company_id, occurred_at DESC)
```

### JSONB usage

JSONB remains appropriate for:

- thesis criteria
- raw source payloads
- extractor metadata
- evidence metadata
- score explanations
- model diagnostics

Do not put frequently filtered business fields exclusively inside JSONB.

---

## 13. API architecture

Base path: `/api/v1`

### Workspace / thesis

```text
GET    /workspaces
GET    /theses
POST   /theses
GET    /theses/{id}
PATCH  /theses/{id}
```

### Discovery

```text
POST   /search-jobs
GET    /search-jobs/{id}
GET    /companies
```

### Company intelligence

```text
GET    /companies/{id}
GET    /companies/{id}/evidence
GET    /companies/{id}/signals
GET    /companies/{id}/timeline
GET    /companies/{id}/relationships
POST   /companies/{id}/refresh
```

### Scoring / decisions

```text
POST   /companies/{id}/score
GET    /theses/{id}/opportunities
GET    /companies/{id}/opportunities/{thesis_id}
GET    /companies/{id}/recommendation
```

### Outreach / pipeline

```text
POST   /companies/{id}/outreach
GET    /companies/{id}/outreach
POST   /companies/{id}/pipeline
POST   /companies/{id}/activities
```

### Exports

```text
POST   /exports
GET    /exports/{id}
```

API responses should expose provenance and score explanations where appropriate rather than returning opaque scalar rankings.

---

## 14. Worker architecture

RQ/Redis remains appropriate initially because the workload is asynchronous, bursty, and easy to partition by job/source/domain.

```text
workers/
├── discovery/
│   ├── run_search_job.py
│   ├── adapters/
│   │   ├── maps.py
│   │   ├── web.py
│   │   ├── licensed_provider.py
│   │   └── base.py
│   └── normalize.py
│
├── resolution/
│   ├── exact_match.py
│   ├── fuzzy_match.py
│   └── merge.py
│
├── evidence/
│   ├── collector.py
│   ├── snapshot.py
│   └── provenance.py
│
├── signals/
│   ├── website.py
│   ├── ownership.py
│   ├── hiring.py
│   ├── reviews.py
│   ├── leadership.py
│   └── events.py
│
├── intelligence/
│   ├── seller_readiness.py
│   ├── thesis_fit.py
│   ├── timing.py
│   ├── access.py
│   ├── competition.py
│   ├── opportunity.py
│   └── recommendations.py
│
├── llm/
│   ├── client.py
│   ├── classify.py
│   ├── deal_brief.py
│   └── outreach.py
│
├── enrichment/
│   ├── contacts.py
│   └── email_verification.py
│
└── exports/
    └── build.py
```

### Queue design

Use separate queues for work with different latency/cost profiles:

```text
critical     → user-requested scoring / company refresh
interactive  → UI-triggered enrichment
standard     → search + signal harvesting
slow         → historical refresh / market mapping
llm          → expensive AI tasks
```

Use idempotency keys for all jobs that can be retried.

---

## 15. Scraping and source handling

Source adapters must implement a common interface:

```python
class SourceAdapter(Protocol):
    def search(self, query: SearchQuery) -> Iterator[RawRecord]: ...
    def fetch(self, external_id: str) -> RawRecord: ...
    def capabilities(self) -> SourceCapabilities: ...
```

### Required behavior

- robots.txt and applicable crawl-delay rules respected
- per-domain rate limits
- exponential backoff + jitter
- retry-after handling
- source-specific circuit breakers
- bounded concurrency
- CAPTCHA/access-control failures quarantined
- no bypassing authentication or technical restrictions
- source terms and licensing reviewed before production use

Playwright is a fallback for permitted JS-rendered pages, not a mechanism for bypassing anti-bot controls.

---

## 16. Entity resolution

Resolution occurs before intelligence scoring.

### Pass 1 — exact

```text
normalized domain
normalized phone
stable source ID
```

### Pass 2 — deterministic composite

```text
name + city + phone
name + address
name + domain
```

### Pass 3 — fuzzy

Use normalized names and geographic context. Require a high threshold and retain the merge decision/evidence.

Never silently merge uncertain companies. A low-confidence candidate should be queued for review or remain separate.

---

## 17. LLM architecture

LLMs are used as bounded intelligence components:

### Good uses

- extracting structured facts from unstructured pages
- classifying ownership/succession language
- summarizing evidence
- proposing adjacent market hypotheses
- generating deal briefs
- generating evidence-grounded outreach drafts

### Bad uses

- inventing revenue
- inventing owner age
- deciding that a company is “for sale” without evidence
- replacing deterministic filters
- writing canonical company fields directly without validation

### Structured output contract

Every LLM extraction should return:

```json
{
  "field": "succession_indicator",
  "value": "no_visible_successor",
  "confidence": 0.84,
  "evidence_ids": ["..."],
  "model_version": "..."
}
```

If evidence is absent, the extractor returns `null`/unknown rather than guessing.

---

## 18. Caching and performance

### Redis

Use Redis for:

- domain rate-limit buckets
- job locks
- dedup locks
- hot company/score cache
- LLM response cache
- short-lived API response cache

### HTTP/evidence cache

Cache permitted page fetches by normalized URL and source policy. Reuse unchanged evidence rather than repeatedly crawling the same page.

### Score memoization

Do not recompute company intelligence when no relevant evidence/signal changed.

```text
same evidence fingerprint
        ↓
skip expensive extraction
        ↓
reuse prior signal state
```

### Database

Use PostgreSQL indexes for ranking/filtering and materialized views only after query profiling demonstrates a need.

---

## 19. Security and tenancy

Supabase/PostgreSQL Row-Level Security is the primary tenant boundary.

Every workspace-owned row must be reachable through a workspace-scoped authorization path.

Rules:

- never trust workspace IDs from the client
- derive workspace membership from authenticated identity
- apply RLS to workspace-owned tables
- service-role credentials only in backend workers
- encrypt secrets through platform secret management
- minimize stored personal data
- provide deletion/export mechanisms
- maintain audit logs for sensitive actions

Supabase Auth should own password credentials; the application should not maintain its own password hash table.

---

## 20. Observability

Track:

### Pipeline metrics

- source success rate
- records discovered/source
- dedup rate
- entity-resolution confidence
- evidence extraction success
- signal extraction success
- job latency

### Intelligence metrics

- score distribution
- score drift by model version
- recommendation acceptance rate
- outreach generation rate
- response rate
- pipeline conversion
- outcome/deal rate

### Cost metrics

- requests/source
- LLM tokens/company
- enrichment cost/company
- average cost per qualified opportunity

The most important product metric is not “leads scraped.” It is:

> **qualified acquisition opportunities discovered per unit of searcher attention.**

---

## 21. Learning loop

The system becomes more valuable when user outcomes are captured.

```text
Signal
  ↓
Score
  ↓
Recommendation
  ↓
User action
  ↓
Owner response / pipeline movement
  ↓
Outcome
  ↓
Calibration + ranking improvement
```

Initially, use outcomes for analytics and calibration rather than immediately training a complex ML model.

Once enough labeled outcomes exist, introduce:

- score calibration
- learning-to-rank
- recommendation policy optimization
- source reliability weighting
- personalized ranking by searcher behavior

The data model already supports this evolution without replacing the core architecture.

---

## 22. Hosting and deployment

### Recommended initial stack

| Layer | Technology | Responsibility |
|---|---|---|
| Web | React + Vite + Tailwind + TanStack Query | product UI |
| API | Python + FastAPI + Pydantic | typed application API |
| Workers | Python + RQ | async pipelines |
| DB | PostgreSQL / Supabase | canonical source of truth |
| Cache/queue | Redis / Upstash | queues, locks, caching |
| Object storage | Supabase Storage | evidence/raw snapshots |
| LLM | provider behind internal adapter | extraction + generation |
| Email verification | provider behind internal adapter | verification |
| Web hosting | Vercel | frontend |
| API/workers | Cloud Run | containerized services |
| CI/CD | GitHub Actions / Cloud Build | test + deploy |

The LLM and enrichment providers should always sit behind internal ports/adapters so the application is not coupled to a single vendor.

---

## 23. Project structure

```text
exitradar/
├── README.md
├── ARCHITECTURE.md
├── LICENSE
├── .env.example
├── docker-compose.yml
│
├── apps/
│   ├── web/
│   │   ├── src/
│   │   │   ├── pages/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── lib/
│   │   └── ...
│   │
│   └── api/
│       └── app/
│           ├── routers/
│           ├── schemas/
│           ├── services/
│           └── core/
│
├── workers/
│   ├── discovery/
│   ├── resolution/
│   ├── evidence/
│   ├── signals/
│   ├── intelligence/
│   ├── llm/
│   ├── enrichment/
│   └── exports/
│
├── packages/
│   └── shared-types/
│
├── infra/
│   ├── supabase/migrations/
│   ├── cloudrun/
│   └── vercel.json
│
├── docs/
│   ├── ExitRadar_ERD.mmd
│   ├── ExitRadar_ERD.svg
│   ├── ExitRadar_ERD.png
│   └── prompts/
│
└── notebooks/
    └── demo_walkthrough.ipynb
```

---

## 24. UI architecture

### Screen 1 — Acquisition Command Center

The default dashboard should answer in seconds:

```text
What changed?
What should I look at?
Why should I care?
What should I do next?
```

Recommended modules:

- opportunity count
- newly actionable targets
- warming targets
- opportunity-window alerts
- market white-space suggestions
- recent score movements
- pipeline outcomes

### Screen 2 — Opportunity table

Columns:

```text
Company | Opportunity | Momentum | Fit | Seller | Access | Competition | Next Action
```

The table is sortable/filterable but the score is never the only explanation.

### Screen 3 — Company opportunity page

```text
ABC HVAC
Opportunity Score 94

WHY THIS COMPANY
✓ Thesis fit: 96
✓ Seller readiness: 88
✓ Timing: 93
✓ Access: 82
✓ Competition advantage: 91

WHY NOW
Leadership changed 43 days ago.
Hiring has contracted for three consecutive observations.
Website activity has remained stale for 14 months.

COUNTER-SIGNALS
• Recent review volume is increasing.
• No explicit succession language found.

NEXT BEST ACTION
Relationship-first outreach this week.
Do not lead with an acquisition pitch.

[View Evidence] [Generate Deal Brief] [Start Monitoring]
```

The counter-signal section is important: it prevents the product from becoming a confirmation-bias engine.

---

## 25. Flagship user journey

```text
1. User writes acquisition thesis in natural language
                 ↓
2. System converts it into structured criteria
                 ↓
3. Market map expands the reachable universe
                 ↓
4. Discovery finds companies from multiple sources
                 ↓
5. Entity resolution creates canonical companies
                 ↓
6. Evidence harvesting begins
                 ↓
7. Signals and temporal changes are extracted
                 ↓
8. Seller readiness + thesis fit are computed
                 ↓
9. Timing + access + competition are added
                 ↓
10. Opportunity Score ranks the universe
                 ↓
11. Decision Engine produces next-best action
                 ↓
12. User reviews evidence and acts
                 ↓
13. Activity/outcome is captured
                 ↓
14. System improves ranking and source reliability
```

This is the product's central differentiation: **the user is not left with 5,000 leads; the system navigates them toward the few opportunities worth attention.**

---

## 26. Phased implementation

### Phase 1 — Intelligence foundation

Build first:

- canonical company model
- source provenance
- evidence store
- signals + signal events
- seller readiness scoring
- acquisition theses
- thesis fit
- opportunity scoring
- evidence-first company page

### Phase 2 — Decision layer

Add:

- timing engine
- next-best-action engine
- monitoring
- opportunity-window alerts
- deal pipeline
- activity tracking

### Phase 3 — Market intelligence

Add:

- company relationship graph
- comparable transactions
- market mapping
- white-space detection
- competition signals
- adjacent-thesis discovery

### Phase 4 — Learning system

Add:

- outcome capture
- source reliability calibration
- score calibration
- learning-to-rank
- personalized ranking
- recommendation optimization

---

## 27. Architectural decisions and trade-offs

### Why PostgreSQL first?

The domain is highly relational: companies, people, sources, evidence, scores, theses, activities, and transactions all have strong relational constraints. PostgreSQL also provides JSONB for flexible evidence metadata and can support graph-like traversals for the initial product.

### Why not a graph database now?

A graph database is attractive conceptually, but introducing one before the relationship queries justify it adds operational complexity and creates synchronization problems. Store relationships relationally first; project them into a graph later if needed.

### Why not a vector database as the core?

Embeddings are useful for semantic company similarity, adjacent-market discovery, and document retrieval. They should augment the canonical relational model, not replace it.

### Why deterministic scoring?

Searchers need to understand and challenge rankings. A deterministic component model makes the system auditable and lets the team improve individual components independently.

### Why not a single “seller probability”?

A probability claim requires high-quality labeled outcomes and calibration. Early in the product lifecycle, a transparent prioritization score is more defensible and more useful operationally.

### Why preserve negative evidence?

Without counter-signals, the system can systematically reinforce its own hypothesis. Negative evidence makes ranking more trustworthy and gives the user a reason to override the system.

---

## 28. Definition of done for the architecture

A company is considered **actionable** only when the system can provide:

1. a canonical company identity,
2. a thesis-fit explanation,
3. a seller-readiness explanation,
4. temporal evidence explaining why timing changed,
5. access/contact context,
6. competition context when available,
7. confidence and missing-data indicators,
8. at least one evidence trail for material claims,
9. a versioned opportunity score,
10. a concrete next-best action.

That is the final product contract:

> **ExitRadar does not just find companies that could sell. It detects when an acquisition opportunity is forming — explains why, tells you when to act, and guides you to the next move.**
