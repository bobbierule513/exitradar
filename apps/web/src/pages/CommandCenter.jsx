import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "../lib/api";
import { useWorkspace } from "../lib/workspace";
import {
  ActionMixChart,
  MomentumSparkline,
  OpportunityRadar,
  RankingChart,
} from "../components/Charts";
import {
  ActionBadge,
  AnimatedNumber,
  ErrorState,
  Loading,
  PageShell,
  ScoreBar,
  SectionLabel,
  fadeUp,
  stagger,
} from "../components/ui";

function daysLeft(iso) {
  if (!iso) return null;
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return null;
  return Math.ceil((dt.getTime() - Date.now()) / 86400000);
}

function SlotCard({ slot, thesisId, onComplete, onSkip, busy }) {
  const { withContext } = useWorkspace();
  const company = slot.company || {};
  const d = daysLeft(slot.window_closes_at);
  const open = slot.status === "open";
  return (
    <div className="border border-line bg-white/60 p-5 shadow-desk">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">
            {slot.kind} · #{slot.rank || "—"} · {slot.status}
          </p>
          <Link
            to={withContext(`/companies/${slot.company_id}`)}
            className="mt-1 block font-display text-2xl text-ink hover:text-signal-deep"
          >
            {company.canonical_name || "Company"}
          </Link>
          <p className="mt-1 text-xs text-ink-mute">
            {company.industry}
            {(company.geo || {}).city ? ` · ${(company.geo || {}).city}` : ""}
          </p>
        </div>
        <div className="text-right">
          {slot.action && <ActionBadge action={slot.action} />}
          {d != null && slot.kind === "outreach" && (
            <p
              className={`mt-2 font-mono text-xs ${
                d <= 7 ? "text-warm" : "text-ink-faint"
              }`}
            >
              {d < 0 ? "Window closed" : `Closes in ${d}d`}
            </p>
          )}
          {slot.expected_lift != null && (
            <p className="mt-2 font-mono text-xs text-signal-deep">
              Lift ~{Number(slot.expected_lift).toFixed(1)}
            </p>
          )}
        </div>
      </div>
      <p className="mt-4 text-sm leading-relaxed text-ink-soft">{slot.reason}</p>
      {slot.chosen_sibling && (
        <p className="mt-2 text-xs text-ink-mute">
          Substitute for{" "}
          <span className="font-medium text-ink">
            {slot.chosen_sibling.canonical_name}
          </span>
        </p>
      )}
      {open && (slot.kind === "outreach" || slot.kind === "research") && (
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-primary text-xs"
            disabled={busy}
            onClick={() => onComplete(slot.id)}
          >
            Complete
          </button>
          {slot.kind === "outreach" && (
            <button
              type="button"
              className="btn-secondary text-xs"
              disabled={busy}
              onClick={() => onSkip(slot.id)}
            >
              Skip
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function CommandCenter() {
  const qc = useQueryClient();
  const { workspaceId, thesisId, isLoading: ctxLoading, withContext } = useWorkspace();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["command-center", workspaceId, thesisId],
    queryFn: () => api.commandCenter(workspaceId, thesisId),
    enabled: Boolean(workspaceId && thesisId),
  });

  const regenMut = useMutation({
    mutationFn: (body) => api.generateBookOfWork(thesisId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["command-center"] });
      qc.invalidateQueries({ queryKey: ["opportunities"] });
    },
  });

  const slotMut = useMutation({
    mutationFn: ({ id, action }) =>
      action === "skip" ? api.skipBookSlot(id, {}) : api.completeBookSlot(id, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["command-center"] });
      qc.invalidateQueries({ queryKey: ["opportunities"] });
    },
  });

  if (ctxLoading || isLoading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={refetch} />;

  const book = data?.book_of_work || {};
  const metrics = data?.book_metrics || {};
  const slots = book.slots || [];
  const outreach = slots.filter((s) => s.kind === "outreach");
  const research = slots.filter((s) => s.kind === "research");
  const hold = slots.filter((s) => s.kind === "hold");
  const stale = slots.filter((s) => s.kind === "stale");
  const lead =
    outreach.find((s) => s.status === "open") ||
    (data?.top_opportunities || [])[0];
  const leadCompany = lead?.company;
  const leadOpp = (data?.top_opportunities || []).find(
    (o) => o.company_id === lead?.company_id
  );

  return (
    <PageShell>
      <motion.section
        variants={stagger}
        initial="initial"
        animate="animate"
        className="relative overflow-hidden border-b border-line pb-10 md:pb-14"
      >
        <div className="grid items-start gap-10 lg:grid-cols-12 lg:gap-8">
          <div className="lg:col-span-6">
            <motion.p variants={fadeUp} className="label">
              This week · {metrics.iso_week || book.iso_week || "—"} · bow-v1
            </motion.p>
            <motion.h1
              variants={fadeUp}
              className="mt-4 max-w-3xl font-display text-[clamp(2.75rem,6.5vw,4.75rem)] leading-[0.95] tracking-tight text-ink"
            >
              Book of Work
            </motion.h1>
            <motion.p
              variants={fadeUp}
              className="mt-5 max-w-xl text-base leading-relaxed text-ink-mute md:text-lg"
            >
              Capacity-aware queue — closing windows first, one company per metro
              cluster, research only when the lift is worth the hours.
            </motion.p>

            <motion.div
              variants={fadeUp}
              className="mt-10 grid gap-8 border-t border-line pt-8 sm:grid-cols-3"
            >
              <Metric
                label="Outreach left"
                value={metrics.outreach_remaining ?? outreach.filter((s) => s.status === "open").length}
                hint={`of ${book.cadence?.max_outreach_per_week ?? 5} capacity`}
                emphasize
              />
              <Metric
                label="Research"
                value={metrics.research_remaining ?? research.filter((s) => s.status === "open").length}
                hint="High-lift gaps"
                warm
              />
              <Metric
                label="Closing ≤7d"
                value={metrics.windows_closing_7d ?? 0}
                hint={`${metrics.stale_count ?? stale.length} stale`}
              />
            </motion.div>

            <motion.div variants={fadeUp} className="mt-6 flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary text-xs"
                disabled={regenMut.isPending}
                onClick={() => regenMut.mutate({ force: true, with_brief: false })}
              >
                {regenMut.isPending ? "Rebuilding…" : "Rebuild week"}
              </button>
              <button
                type="button"
                className="btn-ghost text-xs"
                disabled={regenMut.isPending}
                onClick={() => regenMut.mutate({ force: true, with_brief: true })}
              >
                Write week brief
              </button>
            </motion.div>
          </div>

          <motion.div
            variants={fadeUp}
            className="border border-line bg-white/55 p-5 shadow-desk lg:col-span-6 lg:p-6"
          >
            {leadOpp ? (
              <OpportunityRadar
                label={`Radar · ${leadCompany?.canonical_name || leadOpp.company?.canonical_name || "Lead"}`}
                fit={leadOpp.fit}
                seller={leadOpp.seller}
                timing={leadOpp.timing}
                access={leadOpp.access}
                competition={leadOpp.competition}
              />
            ) : (
              <p className="text-sm text-ink-mute">Run discovery to populate the radar.</p>
            )}
          </motion.div>
        </div>

        {book.brief && (
          <motion.div
            variants={fadeUp}
            className="mt-8 border border-line bg-ink px-6 py-5 text-sm leading-relaxed text-white/80"
          >
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/45">
              Week brief
            </p>
            <p className="mt-3 whitespace-pre-wrap">{book.brief}</p>
          </motion.div>
        )}
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.45 }}
        className="mt-10"
      >
        <SectionLabel>Outreach this week</SectionLabel>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {outreach.length === 0 && (
            <p className="text-sm text-ink-mute">No outreach slots packed.</p>
          )}
          {outreach.map((s) => (
            <SlotCard
              key={s.id}
              slot={s}
              thesisId={data.thesis_id || thesisId}
              busy={slotMut.isPending}
              onComplete={(id) => slotMut.mutate({ id, action: "complete" })}
              onSkip={(id) => slotMut.mutate({ id, action: "skip" })}
            />
          ))}
        </div>
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.45 }}
        className="mt-12"
      >
        <SectionLabel>Research before you call</SectionLabel>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {research.length === 0 && (
            <p className="text-sm text-ink-mute">No high-lift research queued.</p>
          )}
          {research.map((s) => (
            <SlotCard
              key={s.id}
              slot={s}
              thesisId={data.thesis_id || thesisId}
              busy={slotMut.isPending}
              onComplete={(id) => slotMut.mutate({ id, action: "complete" })}
              onSkip={() => {}}
            />
          ))}
        </div>
      </motion.section>

      <div className="mt-12 grid gap-10 border-t border-line pt-10 lg:grid-cols-2">
        <div>
          <SectionLabel>Hold — do not call yet</SectionLabel>
          <ul className="mt-4 divide-y divide-line border-y border-line">
            {hold.slice(0, 8).map((s) => (
              <li key={s.id} className="py-4">
                <Link
                  to={withContext(`/companies/${s.company_id}`)}
                  className="font-medium text-ink hover:text-signal-deep"
                >
                  {s.company?.canonical_name}
                </Link>
                <p className="mt-1 text-xs leading-relaxed text-ink-mute">{s.reason}</p>
              </li>
            ))}
            {hold.length === 0 && (
              <li className="py-4 text-sm text-ink-mute">Nothing on hold.</li>
            )}
          </ul>
        </div>
        <div>
          <SectionLabel>Stale windows</SectionLabel>
          <ul className="mt-4 divide-y divide-line border-y border-line">
            {stale.map((s) => (
              <li key={s.id} className="py-4">
                <Link
                  to={withContext(`/companies/${s.company_id}`)}
                  className="font-medium text-ink hover:text-warm"
                >
                  {s.company?.canonical_name}
                </Link>
                <p className="mt-1 text-xs leading-relaxed text-ink-mute">{s.reason}</p>
              </li>
            ))}
            {stale.length === 0 && (
              <li className="py-4 text-sm text-ink-mute">No expired recommendations.</li>
            )}
          </ul>
        </div>
      </div>

      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25, duration: 0.5 }}
        className="mt-12 grid gap-6 border-t border-line pb-4 pt-10 md:grid-cols-2 lg:grid-cols-3"
      >
        <div className="border border-line bg-white/50 p-5 md:col-span-2 lg:col-span-1">
          <RankingChart opportunities={data?.top_opportunities || []} height={200} />
        </div>
        <div className="border border-line bg-white/50 p-5">
          <ActionMixChart opportunities={data?.top_opportunities || []} />
        </div>
        <div className="border border-line bg-white/50 p-5 md:col-span-2 lg:col-span-1">
          <MomentumSparkline opportunities={data?.top_opportunities || []} />
        </div>
      </motion.section>

      <div className="mt-8 flex justify-end">
        <Link to={withContext("/opportunities")} className="btn-ghost text-xs">
          Full ranked universe →
        </Link>
      </div>
    </PageShell>
  );
}

function Metric({ label, value, hint, emphasize, warm }) {
  return (
    <div>
      <p className="label">{label}</p>
      <p
        className={`mt-2 font-mono text-4xl font-medium tabular-nums md:text-5xl ${
          emphasize ? "text-signal" : warm ? "text-warm" : "text-ink"
        }`}
      >
        <AnimatedNumber value={value} />
      </p>
      <p className="mt-1 text-xs text-ink-faint">{hint}</p>
    </div>
  );
}
