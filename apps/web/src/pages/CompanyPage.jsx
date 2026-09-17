import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../lib/api";
import { useWorkspace } from "../lib/workspace";
import {
  ActionBadge,
  AnimatedNumber,
  ErrorState,
  Loading,
  PageShell,
  ScoreBar,
  fadeUp,
  stagger,
} from "../components/ui";

export default function CompanyPage() {
  const { companyId } = useParams();
  const { thesisId, isLoading: ctxLoading, withContext } = useWorkspace();
  const qc = useQueryClient();
  const [showEvidence, setShowEvidence] = useState(false);
  const [stage, setStage] = useState("identified");

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["opportunity", companyId, thesisId],
    queryFn: () => api.opportunity(companyId, thesisId),
    enabled: Boolean(companyId && thesisId),
  });

  const outreachMut = useMutation({
    mutationFn: () => api.outreach(companyId, { channel: "email", thesis_id: thesisId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["outreach", companyId] }),
  });

  const briefMut = useMutation({
    mutationFn: () => api.dealBrief(companyId, thesisId),
  });

  const pipelineMut = useMutation({
    mutationFn: () => api.pipeline(companyId, { thesis_id: thesisId, stage }),
    onSuccess: () => refetch(),
  });

  const activityMut = useMutation({
    mutationFn: () =>
      api.activity(companyId, {
        activity_type: "note",
        outcome: "reviewed",
        metadata: { source: "ui" },
      }),
  });

  const bookMut = useMutation({
    mutationFn: ({ action }) => {
      const sid = data?.book_slot?.id;
      if (!sid) throw new Error("No book slot");
      return action === "skip" ? api.skipBookSlot(sid, {}) : api.completeBookSlot(sid, {});
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["opportunity", companyId, thesisId] });
      qc.invalidateQueries({ queryKey: ["command-center"] });
      refetch();
    },
  });

  const { data: outreachList } = useQuery({
    queryKey: ["outreach", companyId],
    queryFn: () => api.listOutreach(companyId),
    enabled: !!companyId,
  });

  useEffect(() => {
    const current = data?.pipeline?.stage;
    if (current) setStage(current);
  }, [data?.pipeline?.stage]);

  if (ctxLoading) return <Loading />;
  if (!thesisId) {
    return (
      <PageShell className="mx-auto max-w-lg py-20 text-center">
        <p className="label">Thesis</p>
        <h2 className="mt-3 font-display text-3xl text-ink">No thesis selected</h2>
        <p className="mt-3 text-sm text-ink-mute">
          Choose a thesis before opening a company dossier.
        </p>
        <Link to={withContext("/thesis")} className="btn-primary mt-8 inline-flex">
          Open Thesis
        </Link>
      </PageShell>
    );
  }
  if (isLoading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (!data) return <Loading />;

  const company = data.company || {};
  const expl = data.explanation || {};
  const rec = data.recommendation || {};
  const book = data.book_slot;
  const draft = outreachMut.data || (outreachList || [])[0];

  function bookContextLine() {
    if (!book) return null;
    const d = book.window_closes_at
      ? Math.ceil((new Date(book.window_closes_at).getTime() - Date.now()) / 86400000)
      : null;
    if (book.kind === "outreach") {
      return `In this week’s book · outreach ${book.rank || "—"} · window ${
        d == null ? "—" : d < 0 ? "closed" : `${d}d`
      }`;
    }
    if (book.kind === "research") {
      return `In this week’s book · research slot ${book.rank || "—"} · ${
        book.research_field || "gap"
      }`;
    }
    if (book.kind === "hold") {
      return book.reason || "Held this week — not in outreach capacity.";
    }
    if (book.kind === "stale") {
      return "Stale recommendation — window expired.";
    }
    return null;
  }
  return (
    <PageShell>
      <Link to={withContext("/opportunities")} className="btn-ghost text-xs">
        ← Pipeline
      </Link>

      <motion.header
        variants={stagger}
        initial="initial"
        animate="animate"
        className="mt-6 grid gap-8 border-b border-line pb-10 lg:grid-cols-[1fr_auto]"
      >
        <div>
          <motion.p variants={fadeUp} className="label">
            Company dossier
          </motion.p>
          <motion.h1
            variants={fadeUp}
            className="mt-3 font-display text-[clamp(2.2rem,5vw,3.5rem)] leading-[1.05] tracking-tight"
          >
            {company.canonical_name}
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-3 max-w-xl text-sm text-ink-mute">
            {[company.industry, company.address || `${(company.geo || {}).city || ""}`, company.domain]
              .filter(Boolean)
              .join(" · ")}
          </motion.p>
        </div>
        <motion.div variants={fadeUp} className="lg:text-right">
          <p className="label">Opportunity</p>
          <p className="mt-1 font-mono text-6xl font-medium tabular-nums tracking-tight text-ink md:text-7xl">
            <AnimatedNumber value={data.opportunity_score} />
          </p>
          <div className="mt-3 flex lg:justify-end">
            <ActionBadge action={rec.action} />
          </div>
        </motion.div>
      </motion.header>

      <div className="mt-10 grid gap-12 lg:grid-cols-12">
        <section className="space-y-10 lg:col-span-8">
          <div>
            <h2 className="label">Why this company</h2>
            <div className="mt-5 grid gap-5 sm:grid-cols-2">
              <ScoreBar label="Thesis fit" value={data.fit} tone="signal" />
              <ScoreBar label="Seller readiness" value={data.seller} tone="warm" />
              <ScoreBar label="Timing" value={data.timing} tone="cool" />
              <ScoreBar label="Access" value={data.access} tone="ink" />
              <ScoreBar label="Competition advantage" value={data.competition} tone="muted" />
            </div>
            <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">
              {data.model_version} · {(data.confidence * 100).toFixed(0)}% confidence ·{" "}
              {expl.timing_bucket || "—"}
            </p>
          </div>

          <div className="grid gap-8 sm:grid-cols-2">
            <div>
              <h3 className="font-display text-2xl italic text-signal-deep">Why now</h3>
              <ul className="mt-4 space-y-3">
                {(expl.why_now || []).map((w) => (
                  <li key={w} className="border-l-2 border-signal pl-4 text-sm leading-relaxed text-ink-soft">
                    {w}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="font-display text-2xl italic text-warm">Counter-signals</h3>
              <ul className="mt-4 space-y-3">
                {((expl.counter_signals || []).length
                  ? expl.counter_signals
                  : ["None flagged — still verify independently."]
                ).map((w) => (
                  <li key={w} className="border-l-2 border-warm/50 pl-4 text-sm leading-relaxed text-ink-soft">
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {(expl.missing || []).length > 0 && (
            <p className="border border-dashed border-line bg-paper-wash/50 px-4 py-3 text-sm text-ink-mute">
              Missing data: {(expl.missing || []).join(", ")}
            </p>
          )}
        </section>

        <aside className="space-y-6 lg:col-span-4">
          <div className="panel p-5 shadow-desk">
            <h2 className="label">Next best action</h2>
            <div className="mt-3">
              <ActionBadge action={rec.action} />
            </div>
            <p className="mt-4 text-sm leading-relaxed text-ink-soft">{rec.reason}</p>
            {bookContextLine() && (
              <p className="mt-3 border-l-2 border-signal pl-3 text-xs leading-relaxed text-ink-mute">
                {bookContextLine()}
              </p>
            )}
            {rec.expires_at && (
              <p className="mt-2 font-mono text-[10px] text-ink-faint">
                Expires {new Date(rec.expires_at).toLocaleDateString()}
              </p>
            )}
            <div className="mt-6 flex flex-col gap-2">
              {book && book.status === "open" && (book.kind === "outreach" || book.kind === "research") && (
                <>
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={bookMut.isPending}
                    onClick={() => bookMut.mutate({ action: "complete" })}
                  >
                    Complete book slot
                  </button>
                  {book.kind === "outreach" && (
                    <button
                      type="button"
                      className="btn-secondary"
                      disabled={bookMut.isPending}
                      onClick={() => bookMut.mutate({ action: "skip" })}
                    >
                      Skip (promote substitute)
                    </button>
                  )}
                </>
              )}
              <button
                type="button"
                className="btn-primary"
                onClick={() => outreachMut.mutate()}
                disabled={outreachMut.isPending}
              >
                {outreachMut.isPending ? "Drafting…" : "Generate outreach"}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => briefMut.mutate()}
                disabled={briefMut.isPending}
              >
                Deal brief
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowEvidence((v) => !v)}
              >
                {showEvidence ? "Hide evidence" : "View evidence"}
              </button>
              <button type="button" className="btn-ghost justify-center text-xs" onClick={() => activityMut.mutate()}>
                Log review
              </button>
            </div>
          </div>

          <div className="panel p-5">
            <h2 className="label">Pipeline stage</h2>
            <select className="input mt-3" value={stage} onChange={(e) => setStage(e.target.value)}>
              <option value="identified">Identified</option>
              <option value="researching">Researching</option>
              <option value="outreach">Outreach</option>
              <option value="conversation">Conversation</option>
              <option value="loi">LOI</option>
              <option value="passed">Passed</option>
            </select>
            <button type="button" className="btn-secondary mt-3 w-full" onClick={() => pipelineMut.mutate()}>
              Update stage
            </button>
            {data.pipeline && (
              <p className="mt-3 text-xs text-ink-faint">Current: {data.pipeline.stage}</p>
            )}
          </div>
        </aside>
      </div>

      <AnimatePresence>
        {showEvidence && (
          <motion.section
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-12 overflow-hidden border-t border-line pt-8"
          >
            <h2 className="label">Evidence trail</h2>
            <ul className="mt-5 space-y-4">
              {(data.evidence || []).map((e, i) => (
                <motion.li
                  key={e.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="border-b border-line pb-4"
                >
                  <div className="flex justify-between gap-2 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
                    <span>
                      {e.source} · {e.type}
                    </span>
                    <span>{(e.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <p className="mt-2 text-sm text-ink-soft">{e.snippet}</p>
                </motion.li>
              ))}
            </ul>
            <div className="mt-6 flex flex-wrap gap-2">
              {(data.signals || []).map((s) => (
                <span
                  key={s.id}
                  className="border border-line bg-white/60 px-2 py-1 font-mono text-[11px] text-ink-mute"
                >
                  {s.signal_type}:{" "}
                  {typeof s.value === "object" ? JSON.stringify(s.value) : String(s.value)}
                </span>
              ))}
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {briefMut.data && (
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-10 border border-line bg-white/60 p-6"
          >
            <h2 className="font-display text-2xl">Deal brief</h2>
            <p className="mt-3 text-sm leading-relaxed text-ink-soft">{briefMut.data.deal_brief}</p>
          </motion.section>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {draft && (
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-10 border border-ink bg-ink p-6 text-paper-elev md:p-8"
          >
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/40">
              Outreach draft
            </p>
            <h2 className="mt-2 font-display text-2xl text-white">{draft.subject}</h2>
            <pre className="mt-5 whitespace-pre-wrap font-sans text-sm leading-relaxed text-white/75">
              {draft.body}
            </pre>
            <p className="mt-6 font-mono text-[10px] text-white/35">
              Evidence refs: {(draft.evidence_refs || []).join(", ") || "none"}
            </p>
          </motion.section>
        )}
      </AnimatePresence>
    </PageShell>
  );
}
