-- ExitRadar full ERD migration
-- PostgreSQL / Supabase

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users (profile mirror of auth.users)
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workspaces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  plan TEXT NOT NULL DEFAULT 'free',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workspace_members (
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member',
  PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE IF NOT EXISTS acquisition_theses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  criteria JSONB NOT NULL DEFAULT '{}',
  strategy JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS search_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  thesis_id UUID NOT NULL REFERENCES acquisition_theses(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'queued',
  query JSONB NOT NULL DEFAULT '{}',
  stats JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  search_job_id UUID NOT NULL REFERENCES search_jobs(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  external_id TEXT,
  payload JSONB NOT NULL,
  content_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (search_job_id, source, external_id)
);

CREATE TABLE IF NOT EXISTS companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name TEXT NOT NULL,
  domain TEXT,
  phone_norm TEXT,
  address TEXT,
  geo JSONB,
  industry TEXT,
  revenue_est NUMERIC,
  founded_year INT,
  workspace_id UUID REFERENCES workspaces(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS companies_domain_unique
  ON companies (lower(domain)) WHERE domain IS NOT NULL AND domain <> '';

CREATE INDEX IF NOT EXISTS companies_geo_industry_idx
  ON companies ((geo->>'country'), (geo->>'state'), industry);

CREATE TABLE IF NOT EXISTS company_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  external_id TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.5,
  raw_ref UUID REFERENCES raw_leads(id),
  UNIQUE (source, external_id)
);

CREATE TABLE IF NOT EXISTS contacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  name TEXT,
  title TEXT,
  email TEXT,
  phone TEXT,
  linkedin TEXT,
  owner_estimate BOOLEAN NOT NULL DEFAULT false,
  confidence REAL NOT NULL DEFAULT 0.5
);

CREATE INDEX IF NOT EXISTS contacts_company_idx ON contacts(company_id);

CREATE TABLE IF NOT EXISTS evidence_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  type TEXT NOT NULL,
  url TEXT,
  snippet TEXT,
  snapshot_path TEXT,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  confidence REAL NOT NULL DEFAULT 0.7,
  metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  signal_type TEXT NOT NULL,
  value JSONB,
  confidence REAL NOT NULL DEFAULT 0.5,
  first_observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS signals_company_type_idx
  ON signals(company_id, signal_type, last_observed_at DESC);

CREATE TABLE IF NOT EXISTS signal_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  signal_id UUID REFERENCES signals(id) ON DELETE SET NULL,
  signal_type TEXT NOT NULL,
  previous_value JSONB,
  current_value JSONB,
  delta JSONB,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS signal_events_company_idx
  ON signal_events(company_id, observed_at DESC);

CREATE TABLE IF NOT EXISTS signal_evidence (
  signal_id UUID NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
  evidence_id UUID NOT NULL REFERENCES evidence_items(id) ON DELETE CASCADE,
  PRIMARY KEY (signal_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS seller_readiness_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  exit_window REAL,
  succession_vacuum REAL,
  digital_decay REAL,
  stagnation REAL,
  recent_change REAL,
  sri_total REAL NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.5,
  model_version TEXT NOT NULL,
  explanation JSONB NOT NULL DEFAULT '{}',
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS seller_scores_company_idx
  ON seller_readiness_scores(company_id, computed_at DESC);

CREATE TABLE IF NOT EXISTS opportunity_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  thesis_id UUID NOT NULL REFERENCES acquisition_theses(id) ON DELETE CASCADE,
  fit REAL,
  seller REAL,
  timing REAL,
  access REAL,
  competition REAL,
  opportunity_score REAL NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.5,
  model_version TEXT NOT NULL,
  explanation JSONB NOT NULL DEFAULT '{}',
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS opportunity_scores_thesis_rank_idx
  ON opportunity_scores(thesis_id, opportunity_score DESC);

CREATE INDEX IF NOT EXISTS opportunity_scores_company_thesis_idx
  ON opportunity_scores(company_id, thesis_id, computed_at DESC);

CREATE TABLE IF NOT EXISTS score_evidence (
  score_id UUID NOT NULL,
  evidence_id UUID NOT NULL REFERENCES evidence_items(id) ON DELETE CASCADE,
  score_type TEXT NOT NULL,
  PRIMARY KEY (score_id, evidence_id, score_type)
);

CREATE TABLE IF NOT EXISTS recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  thesis_id UUID NOT NULL REFERENCES acquisition_theses(id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  priority INT NOT NULL DEFAULT 50,
  reason TEXT,
  status TEXT NOT NULL DEFAULT 'open',
  model_version TEXT NOT NULL,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS recommendations_thesis_status_idx
  ON recommendations(thesis_id, status, priority DESC);

CREATE TABLE IF NOT EXISTS outreach_drafts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
  channel TEXT NOT NULL DEFAULT 'email',
  subject TEXT,
  body TEXT,
  prompt_version TEXT,
  evidence_refs JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS deal_pipeline (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  thesis_id UUID NOT NULL REFERENCES acquisition_theses(id) ON DELETE CASCADE,
  stage TEXT NOT NULL DEFAULT 'identified',
  probability REAL NOT NULL DEFAULT 0.1,
  notes TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (company_id, thesis_id)
);

CREATE TABLE IF NOT EXISTS activities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
  recommendation_id UUID REFERENCES recommendations(id) ON DELETE SET NULL,
  activity_type TEXT NOT NULL,
  outcome TEXT,
  metadata JSONB NOT NULL DEFAULT '{}',
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS activities_company_idx
  ON activities(company_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS exports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  file_path TEXT,
  filters JSONB NOT NULL DEFAULT '{}',
  row_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS compliance_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  source TEXT,
  detail TEXT,
  robots_allowed BOOLEAN,
  policy_allowed BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS company_relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  related_company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  relationship_type TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.5,
  UNIQUE (company_id, related_company_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS company_relationships_idx
  ON company_relationships(company_id, relationship_type);

CREATE TABLE IF NOT EXISTS transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  target_company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
  buyer_company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
  transaction_type TEXT,
  announced_value NUMERIC,
  announced_at DATE,
  evidence JSONB NOT NULL DEFAULT '{}'
);

-- Helper: workspace membership check for RLS
CREATE OR REPLACE FUNCTION public.is_workspace_member(ws_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM workspace_members wm
    WHERE wm.workspace_id = ws_id AND wm.user_id = auth.uid()
  );
$$;

-- Enable RLS
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE acquisition_theses ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE exports ENABLE ROW LEVEL SECURITY;

CREATE POLICY workspaces_member_select ON workspaces
  FOR SELECT USING (public.is_workspace_member(id) OR owner_id = auth.uid());

CREATE POLICY workspace_members_select ON workspace_members
  FOR SELECT USING (public.is_workspace_member(workspace_id) OR user_id = auth.uid());

CREATE POLICY theses_member_all ON acquisition_theses
  FOR ALL USING (public.is_workspace_member(workspace_id));

CREATE POLICY search_jobs_via_thesis ON search_jobs
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM acquisition_theses t
      WHERE t.id = search_jobs.thesis_id AND public.is_workspace_member(t.workspace_id)
    )
  );

CREATE POLICY exports_member ON exports
  FOR ALL USING (public.is_workspace_member(workspace_id));

-- Companies are workspace-scoped when workspace_id is set
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
CREATE POLICY companies_member ON companies
  FOR ALL USING (
    workspace_id IS NULL OR public.is_workspace_member(workspace_id)
  );
