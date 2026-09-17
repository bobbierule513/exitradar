import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { api } from "../lib/api";
import { useWorkspace } from "../lib/workspace";
import {
  ActionBadge,
  ErrorState,
  Loading,
  PageShell,
  fadeUp,
  stagger,
} from "../components/ui";

export default function Opportunities() {
  const [filter, setFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("ALL");
  const [bookFilter, setBookFilter] = useState("ALL");
  const { workspaceId, thesisId, isLoading: ctxLoading, withContext } = useWorkspace();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["opportunities", thesisId],
    queryFn: () => api.opportunities(thesisId),
    enabled: Boolean(thesisId),
  });

  const exportMut = useMutation({
    mutationFn: async () => {
      const meta = await api.createExport({
        workspace_id: workspaceId,
        thesis_id: thesisId,
        format: "csv",
      });
      const csv = await api.getExport(meta.id, "csv");
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `exitradar-opportunities-${meta.id.slice(0, 8)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      return meta;
    },
  });

  const rows = useMemo(() => {
    let list = data || [];
    if (filter) {
      const q = filter.toLowerCase();
      list = list.filter((o) =>
        (o.company?.canonical_name || "").toLowerCase().includes(q)
      );
    }
    if (actionFilter !== "ALL") {
      list = list.filter((o) => o.recommendation?.action === actionFilter);
    }
    if (bookFilter === "IN_BOOK") {
      list = list.filter((o) => o.book_slot === "outreach" || o.book_slot === "research");
    } else if (bookFilter === "HOLD") {
      list = list.filter((o) => o.book_slot === "hold");
    } else if (bookFilter === "STALE") {
      list = list.filter((o) => o.book_slot === "stale");
    }
    return list;
  }, [data, filter, actionFilter, bookFilter]);
  if (ctxLoading || isLoading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={refetch} />;

  return (
    <PageShell>
      <motion.div
        variants={stagger}
        initial="initial"
        animate="animate"
        className="flex flex-wrap items-end justify-between gap-6 border-b border-line pb-8"
      >
        <div>
          <motion.p variants={fadeUp} className="label">
            Ranked universe
          </motion.p>
          <motion.h1
            variants={fadeUp}
            className="mt-2 font-display text-4xl tracking-tight md:text-5xl"
          >
            Pipeline
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-3 max-w-md text-sm text-ink-mute">
            Scores are decision weights — inspect evidence before you act.
          </motion.p>
        </div>
        <motion.button
          variants={fadeUp}
          type="button"
          className="btn-secondary"
          onClick={() => exportMut.mutate()}
          disabled={exportMut.isPending}
        >
          {exportMut.isPending ? "Preparing…" : "Export CSV"}
        </motion.button>
      </motion.div>

      <div className="mt-6 flex flex-wrap gap-3">
        <input
          className="input max-w-xs"
          placeholder="Filter companies…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <select
          className="input max-w-[220px]"
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
        >
          <option value="ALL">All actions</option>
          <option value="CONTACT_NOW">Contact now</option>
          <option value="RELATIONSHIP_FIRST">Relationship first</option>
          <option value="RESEARCH_MORE">Research more</option>
          <option value="MONITOR">Monitor</option>
          <option value="DEPRIORITIZE">Deprioritize</option>
        </select>
        <select
          className="input max-w-[200px]"
          value={bookFilter}
          onChange={(e) => setBookFilter(e.target.value)}
        >
          <option value="ALL">All book slots</option>
          <option value="IN_BOOK">In book (outreach/research)</option>
          <option value="HOLD">Hold</option>
          <option value="STALE">Stale</option>
        </select>
      </div>

      {/* Desktop table */}
      <div className="mt-8 hidden overflow-x-auto md:block">
        <table className="w-full min-w-[960px] text-left">
          <thead>
            <tr className="border-b border-line">
              {[
                "Company",
                "Opp",
                "Fit",
                "Seller",
                "Timing",
                "Access",
                "Comp",
                "Book",
                "Action",
              ].map((h) => (
                <th key={h} className="label pb-3 pr-3 font-semibold">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((o, i) => (
              <motion.tr
                key={o.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="group border-b border-line/80 transition hover:bg-white/50"
              >
                <td className="py-4 pr-3">
                  <Link
                    className="font-medium text-ink transition group-hover:text-signal-deep"
                    to={withContext(`/companies/${o.company_id}`)}
                  >
                    {o.company?.canonical_name}
                  </Link>
                  <div className="mt-0.5 text-xs text-ink-faint">
                    {(o.company?.geo || {}).city} {(o.company?.geo || {}).state}
                  </div>
                </td>
                <td className="py-4 pr-3">
                  <span className="font-mono text-lg font-medium tabular-nums">
                    {Number(o.opportunity_score).toFixed(0)}
                  </span>
                  <div className="text-[10px] text-ink-faint">
                    {(o.confidence * 100).toFixed(0)}% conf
                  </div>
                </td>
                {["fit", "seller", "timing", "access", "competition"].map((k) => (
                  <td key={k} className="py-4 pr-3 font-mono text-sm tabular-nums text-ink-soft">
                    {Number(o[k]).toFixed(0)}
                  </td>
                ))}
                <td className="py-4 pr-3 font-mono text-[11px] uppercase tracking-wide text-ink-mute">
                  {o.book_slot || "—"}
                </td>
                <td className="py-4">
                  <ActionBadge action={o.recommendation?.action} />
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards as interaction containers */}
      <ul className="mt-6 space-y-3 md:hidden">
        {rows.map((o) => (
          <li key={o.id}>
            <Link
              to={withContext(`/companies/${o.company_id}`)}
              className="panel block p-4 shadow-desk"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{o.company?.canonical_name}</p>
                  <p className="text-xs text-ink-faint">
                    {(o.company?.geo || {}).city} {(o.company?.geo || {}).state}
                  </p>
                </div>
                <span className="font-mono text-2xl font-medium">
                  {Number(o.opportunity_score).toFixed(0)}
                </span>
              </div>
              <div className="mt-3">
                <ActionBadge action={o.recommendation?.action} />
              </div>
            </Link>
          </li>
        ))}
      </ul>

      {!rows.length && (
        <p className="mt-12 text-center text-sm text-ink-mute">No matching opportunities.</p>
      )}
    </PageShell>
  );
}
