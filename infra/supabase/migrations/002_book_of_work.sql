-- Book of Work: workspace cadence + weekly plans/slots
-- Apply after 001_initial_erd.sql

ALTER TABLE workspaces
  ADD COLUMN IF NOT EXISTS settings JSONB NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS book_of_work_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  thesis_id UUID NOT NULL REFERENCES acquisition_theses(id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  iso_week TEXT NOT NULL,
  model_version TEXT NOT NULL DEFAULT 'bow-v1',
  cadence JSONB NOT NULL DEFAULT '{}',
  stats JSONB NOT NULL DEFAULT '{}',
  brief TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS book_of_work_plans_thesis_week_idx
  ON book_of_work_plans(thesis_id, iso_week, status);

CREATE TABLE IF NOT EXISTS book_of_work_slots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id UUID NOT NULL REFERENCES book_of_work_plans(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  rank INT NOT NULL DEFAULT 0,
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  recommendation_id UUID REFERENCES recommendations(id) ON DELETE SET NULL,
  cluster_id TEXT,
  window_closes_at TIMESTAMPTZ,
  reason TEXT,
  expected_lift REAL,
  research_field TEXT,
  lift_per_hour REAL,
  chosen_sibling_id UUID REFERENCES companies(id) ON DELETE SET NULL,
  action TEXT,
  opportunity_score REAL,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS book_of_work_slots_plan_idx
  ON book_of_work_slots(plan_id, kind, rank);

CREATE INDEX IF NOT EXISTS book_of_work_slots_company_idx
  ON book_of_work_slots(company_id, status);

ALTER TABLE book_of_work_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE book_of_work_slots ENABLE ROW LEVEL SECURITY;

CREATE POLICY book_plans_member ON book_of_work_plans
  FOR ALL USING (public.is_workspace_member(workspace_id));

CREATE POLICY book_slots_via_plan ON book_of_work_slots
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM book_of_work_plans p
      WHERE p.id = book_of_work_slots.plan_id
        AND public.is_workspace_member(p.workspace_id)
    )
  );
