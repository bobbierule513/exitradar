import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../lib/api";
import { useWorkspace } from "../lib/workspace";
import CriteriaSummary from "../components/CriteriaSummary";
import { ErrorState, Loading, PageShell, fadeUp, stagger } from "../components/ui";

const EMPTY_FORM = {
  name: "",
  industries: "HVAC",
  states: "CA, TX, FL, AZ",
  country: "US",
  revenueMin: "2000000",
  revenueMax: "10000000",
  ownerOperated: true,
  minYears: "15",
  keywords: "commercial HVAC, residential HVAC, service",
  location: "Phoenix, AZ",
};

function parseList(value) {
  return value
    .split(/[,;\n]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function formToCriteria(form) {
  const industries = parseList(form.industries);
  const states = parseList(form.states).map((s) => s.toUpperCase());
  const keywords = parseList(form.keywords);
  const revenue_min = form.revenueMin ? Number(form.revenueMin) : null;
  const revenue_max = form.revenueMax ? Number(form.revenueMax) : null;
  const min_years_in_business = form.minYears ? Number(form.minYears) : null;

  return {
    industries,
    geographies: [
      {
        country: form.country || "US",
        states,
        cities: [],
      },
    ],
    revenue_min: Number.isFinite(revenue_min) ? revenue_min : null,
    revenue_max: Number.isFinite(revenue_max) ? revenue_max : null,
    owner_operated: Boolean(form.ownerOperated),
    min_years_in_business: Number.isFinite(min_years_in_business)
      ? min_years_in_business
      : null,
    keywords: keywords.length ? keywords : industries,
  };
}

function JobProgress({ job }) {
  const { withContext } = useWorkspace();
  if (!job) return null;
  const stats = job.stats || {};
  const done = job.status === "completed";
  const failed = job.status === "failed";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="border border-line bg-white/70 p-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="label">Discovery run</p>
          <p className="mt-1 text-sm text-ink-soft">
            {failed && "Something went wrong — try again."}
            {!failed && !done && "Searching sources, resolving companies, scoring…"}
            {done && "Discovery finished. Opportunities are ranked on Radar & Pipeline."}
          </p>
        </div>
        <span
          className={`action-chip ${
            done
              ? "bg-signal-soft text-signal-deep"
              : failed
                ? "bg-danger-soft text-danger"
                : "bg-cool-soft text-cool"
          }`}
        >
          {job.status}
        </span>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-4 border-t border-line pt-4">
        <div>
          <p className="label">Discovered</p>
          <p className="mt-1 font-mono text-2xl text-ink">{stats.discovered ?? "—"}</p>
        </div>
        <div>
          <p className="label">Scored</p>
          <p className="mt-1 font-mono text-2xl text-ink">{stats.scored ?? "—"}</p>
        </div>
        <div>
          <p className="label">Phase</p>
          <p className="mt-1 font-mono text-sm uppercase tracking-wider text-ink-mute">
            {stats.phase || job.status}
          </p>
        </div>
      </div>

      {done && (
        <div className="mt-5 flex flex-wrap gap-3">
          <Link to={withContext("/")} className="btn-primary">
            Open Radar
          </Link>
          <Link to={withContext("/opportunities")} className="btn-secondary">
            View Pipeline
          </Link>
        </div>
      )}
    </motion.div>
  );
}

export default function ThesisPage() {
  const qc = useQueryClient();
  const { workspaceId, thesisId, setThesisId, withContext } = useWorkspace();
  const [mode, setMode] = useState("search"); // "search" | "form"
  const [query, setQuery] = useState(
    "US-based HVAC service businesses, $2–10M revenue, owner-operated, preferably 15+ years old, CA/TX/FL/AZ"
  );
  const [form, setForm] = useState(EMPTY_FORM);
  const [jobId, setJobId] = useState(null);
  const [activeThesis, setActiveThesis] = useState(null);
  const [statusMsg, setStatusMsg] = useState("");
  const [outreachCap, setOutreachCap] = useState(5);
  const [researchCap, setResearchCap] = useState(4);

  const { data: theses, isLoading, error, refetch } = useQuery({
    queryKey: ["theses", workspaceId],
    queryFn: () => api.theses(workspaceId),
    enabled: Boolean(workspaceId),
  });

  const { data: cadence } = useQuery({
    queryKey: ["cadence", workspaceId, thesisId],
    queryFn: () => api.getCadence(workspaceId, thesisId),
    enabled: Boolean(workspaceId),
  });

  const cadenceMut = useMutation({
    mutationFn: () =>
      api.patchCadence(workspaceId, {
        max_outreach_per_week: Number(outreachCap),
        max_research_slots: Number(researchCap),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["cadence"] });
      await qc.invalidateQueries({ queryKey: ["command-center"] });
    },
  });

  const existing = useMemo(
    () => (theses || []).find((t) => t.id === thesisId) || (theses || [])[0] || null,
    [theses, thesisId]
  );
  const displayThesis = useMemo(() => {
    if (activeThesis && activeThesis.id === thesisId) return activeThesis;
    return existing;
  }, [activeThesis, thesisId, existing]);

  // Sync cadence inputs when loaded
  useEffect(() => {
    if (cadence?.max_outreach_per_week != null) setOutreachCap(cadence.max_outreach_per_week);
    if (cadence?.max_research_slots != null) setResearchCap(cadence.max_research_slots);
  }, [cadence]);

  const { data: job } = useQuery({
    queryKey: ["search-job", jobId],
    queryFn: () => api.getSearchJob(jobId),
    enabled: !!jobId,
    refetchInterval: (q) =>
      q.state.data?.status === "completed" || q.state.data?.status === "failed" ? false : 1200,
  });

  const runDiscovery = async (thesis, location) => {
    const jobRes = await api.searchJobs({
      thesis_id: thesis.id,
      location: location || "United States",
      max_results: 10,
    });
    setJobId(jobRes.id);
    await qc.invalidateQueries({ queryKey: ["opportunities"] });
    await qc.invalidateQueries({ queryKey: ["command-center"] });
    return jobRes;
  };

  const semanticMut = useMutation({
    mutationFn: async () => {
      setStatusMsg("Understanding your query…");
      const thesis = await api.createThesis({
        workspace_id: workspaceId,
        name: "Semantic search",
        natural_language: query.trim(),
      });
      setActiveThesis(thesis);
      setThesisId(thesis.id);
      setStatusMsg("Running discovery & scoring…");
      const loc =
        (thesis.criteria?.geographies?.[0]?.states || [])[0]
          ? `${thesis.criteria.geographies[0].states[0]}, US`
          : "Phoenix, AZ";
      await runDiscovery(thesis, loc);
      return thesis;
    },
    onSuccess: async () => {
      setStatusMsg("");
      await qc.invalidateQueries({ queryKey: ["theses"] });
    },
    onError: () => setStatusMsg(""),
  });

  const formMut = useMutation({
    mutationFn: async () => {
      const criteria = formToCriteria(form);
      const name = form.name.trim() || `${criteria.industries[0] || "Acquisition"} thesis`;
      setStatusMsg("Saving thesis…");
      const thesis = await api.createThesis({
        workspace_id: workspaceId,
        name,
        criteria,
        strategy: {
          rationale: "Structured thesis from guided research form",
          adjacent_segments: [],
        },
      });
      setActiveThesis(thesis);
      setThesisId(thesis.id);
      setStatusMsg("Running discovery & scoring…");
      await runDiscovery(thesis, form.location.trim() || "Phoenix, AZ");
      return thesis;
    },
    onSuccess: async () => {
      setStatusMsg("");
      await qc.invalidateQueries({ queryKey: ["theses"] });
    },
    onError: () => setStatusMsg(""),
  });

  const busy = semanticMut.isPending || formMut.isPending;

  if (isLoading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={refetch} />;

  return (
    <PageShell className="mx-auto max-w-3xl">
      <motion.div variants={stagger} initial="initial" animate="animate">
        <motion.p variants={fadeUp} className="label">
          Research setup
        </motion.p>
        <motion.h1
          variants={fadeUp}
          className="mt-3 font-display text-4xl tracking-tight md:text-5xl"
        >
          Define your thesis
        </motion.h1>
        <motion.p variants={fadeUp} className="mt-4 max-w-2xl text-base text-ink-mute">
          Choose how you want to brief ExitRadar — a natural-language search, or a detailed
          research form. We turn either into ranked opportunities, not a JSON dump.
        </motion.p>
      </motion.div>

      {/* Mode switcher */}
      <div className="mt-10 grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => setMode("search")}
          className={`border px-5 py-5 text-left transition ${
            mode === "search"
              ? "border-ink bg-ink text-white"
              : "border-line bg-white/60 text-ink hover:border-ink/40"
          }`}
        >
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] opacity-60">
            Option A
          </p>
          <p className="mt-2 font-display text-2xl">Semantic search</p>
          <p className={`mt-2 text-sm leading-relaxed ${mode === "search" ? "text-white/70" : "text-ink-mute"}`}>
            Describe what you want in plain English. We parse intent and find matching companies.
          </p>
        </button>
        <button
          type="button"
          onClick={() => setMode("form")}
          className={`border px-5 py-5 text-left transition ${
            mode === "form"
              ? "border-ink bg-ink text-white"
              : "border-line bg-white/60 text-ink hover:border-ink/40"
          }`}
        >
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] opacity-60">
            Option B
          </p>
          <p className="mt-2 font-display text-2xl">Guided form</p>
          <p className={`mt-2 text-sm leading-relaxed ${mode === "form" ? "text-white/70" : "text-ink-mute"}`}>
            Fill industries, geography, revenue, ownership, and more — full control over the brief.
          </p>
        </button>
      </div>

      <AnimatePresence mode="wait">
        {mode === "search" ? (
          <motion.section
            key="search"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="mt-8 space-y-4"
          >
            <label className="label" htmlFor="semantic-query">
              What are you looking for?
            </label>
            <div className="relative">
              <input
                id="semantic-query"
                className="input py-4 pr-28 text-base"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && query.trim() && !busy) semanticMut.mutate();
                }}
                placeholder="e.g. Owner-operated HVAC companies in Texas under $10M…"
              />
              <button
                type="button"
                className="btn-primary absolute right-2 top-1/2 -translate-y-1/2"
                disabled={busy || !query.trim()}
                onClick={() => semanticMut.mutate()}
              >
                {semanticMut.isPending ? "Searching…" : "Search"}
              </button>
            </div>
            <p className="text-xs text-ink-faint">
              Semantic parse → structured thesis → discovery → scored opportunities.
              {statusMsg ? ` ${statusMsg}` : ""}
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              {[
                "Dental practices for sale signals in Florida",
                "Plumbing businesses CA/AZ, owner-operated, 15+ years",
                "Commercial HVAC roll-up targets $2–8M revenue",
              ].map((hint) => (
                <button
                  key={hint}
                  type="button"
                  className="rounded-md border border-line bg-paper-wash/80 px-3 py-1.5 text-left text-xs text-ink-mute transition hover:border-signal hover:text-ink"
                  onClick={() => setQuery(hint)}
                >
                  {hint}
                </button>
              ))}
            </div>
          </motion.section>
        ) : (
          <motion.section
            key="form"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="mt-8 space-y-5"
          >
            <div>
              <label className="label" htmlFor="f-name">
                Thesis name
              </label>
              <input
                id="f-name"
                className="input mt-2"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Sunbelt HVAC roll-up"
              />
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="f-industries">
                  Industries
                </label>
                <input
                  id="f-industries"
                  className="input mt-2"
                  value={form.industries}
                  onChange={(e) => setForm({ ...form, industries: e.target.value })}
                  placeholder="HVAC, plumbing"
                />
                <p className="mt-1 text-[11px] text-ink-faint">Comma-separated</p>
              </div>
              <div>
                <label className="label" htmlFor="f-keywords">
                  Keywords
                </label>
                <input
                  id="f-keywords"
                  className="input mt-2"
                  value={form.keywords}
                  onChange={(e) => setForm({ ...form, keywords: e.target.value })}
                  placeholder="commercial, service"
                />
              </div>
            </div>

            <div className="grid gap-5 sm:grid-cols-3">
              <div>
                <label className="label" htmlFor="f-country">
                  Country
                </label>
                <input
                  id="f-country"
                  className="input mt-2"
                  value={form.country}
                  onChange={(e) => setForm({ ...form, country: e.target.value })}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="label" htmlFor="f-states">
                  States / regions
                </label>
                <input
                  id="f-states"
                  className="input mt-2"
                  value={form.states}
                  onChange={(e) => setForm({ ...form, states: e.target.value })}
                  placeholder="CA, TX, FL"
                />
              </div>
            </div>

            <div className="grid gap-5 sm:grid-cols-3">
              <div>
                <label className="label" htmlFor="f-rmin">
                  Min revenue (USD)
                </label>
                <input
                  id="f-rmin"
                  type="number"
                  className="input mt-2"
                  value={form.revenueMin}
                  onChange={(e) => setForm({ ...form, revenueMin: e.target.value })}
                />
              </div>
              <div>
                <label className="label" htmlFor="f-rmax">
                  Max revenue (USD)
                </label>
                <input
                  id="f-rmax"
                  type="number"
                  className="input mt-2"
                  value={form.revenueMax}
                  onChange={(e) => setForm({ ...form, revenueMax: e.target.value })}
                />
              </div>
              <div>
                <label className="label" htmlFor="f-years">
                  Min years in business
                </label>
                <input
                  id="f-years"
                  type="number"
                  className="input mt-2"
                  value={form.minYears}
                  onChange={(e) => setForm({ ...form, minYears: e.target.value })}
                />
              </div>
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="f-loc">
                  Discovery location
                </label>
                <input
                  id="f-loc"
                  className="input mt-2"
                  value={form.location}
                  onChange={(e) => setForm({ ...form, location: e.target.value })}
                  placeholder="City, State"
                />
              </div>
              <div className="flex items-end">
                <label className="flex cursor-pointer items-center gap-3 border border-line bg-white/60 px-4 py-3">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-[var(--signal)]"
                    checked={form.ownerOperated}
                    onChange={(e) => setForm({ ...form, ownerOperated: e.target.checked })}
                  />
                  <span className="text-sm text-ink-soft">Prefer owner-operated businesses</span>
                </label>
              </div>
            </div>

            <button
              type="button"
              className="btn-primary"
              disabled={busy}
              onClick={() => formMut.mutate()}
            >
              {formMut.isPending ? "Running research…" : "Save thesis & find companies"}
            </button>
            {statusMsg && <p className="text-xs text-ink-faint">{statusMsg}</p>}
          </motion.section>
        )}
      </AnimatePresence>

      {/* Human-readable criteria + job progress */}
      <div className="mt-10 space-y-6 border-t border-line pt-10">
        <section className="border border-line bg-white/60 p-5">
          <p className="label">Weekly cadence</p>
          <p className="mt-2 text-sm text-ink-mute">
            Caps how many owner conversations and research tasks the Book of Work packs each week.
          </p>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <div>
              <label className="label" htmlFor="cadence-outreach">
                Max outreach / week
              </label>
              <input
                id="cadence-outreach"
                type="number"
                min={1}
                max={20}
                className="input mt-2"
                value={outreachCap}
                onChange={(e) => setOutreachCap(e.target.value)}
              />
            </div>
            <div>
              <label className="label" htmlFor="cadence-research">
                Max research slots
              </label>
              <input
                id="cadence-research"
                type="number"
                min={0}
                max={20}
                className="input mt-2"
                value={researchCap}
                onChange={(e) => setResearchCap(e.target.value)}
              />
            </div>
            <div className="flex items-end">
              <button
                type="button"
                className="btn-secondary w-full"
                disabled={cadenceMut.isPending}
                onClick={() => cadenceMut.mutate()}
              >
                {cadenceMut.isPending ? "Saving…" : "Save cadence"}
              </button>
            </div>
          </div>
        </section>

        {displayThesis && (
          <CriteriaSummary
            name={displayThesis.name}
            criteria={displayThesis.criteria}
            strategy={displayThesis.strategy}
          />
        )}

        {displayThesis && !jobId && !busy && (
          <button
            type="button"
            className="btn-secondary"
            onClick={() =>
              runDiscovery(
                displayThesis,
                mode === "form" ? form.location : "Phoenix, AZ"
              )
            }
          >
            Re-run discovery on this thesis
          </button>
        )}

        <JobProgress job={job} />

        {(semanticMut.isError || formMut.isError) && (
          <p className="text-sm text-danger">
            {(semanticMut.error || formMut.error)?.message || "Request failed"}
          </p>
        )}
      </div>
    </PageShell>
  );
}
