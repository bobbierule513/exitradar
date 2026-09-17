/** Human-readable thesis criteria — never raw JSON. */

function Chip({ children }) {
  return (
    <span className="inline-flex items-center rounded-md border border-line bg-white/70 px-2.5 py-1 text-xs font-medium text-ink-soft">
      {children}
    </span>
  );
}

function formatMoney(n) {
  if (n == null || n === "") return null;
  const num = Number(n);
  if (Number.isNaN(num)) return null;
  if (num >= 1_000_000) return `$${(num / 1_000_000).toFixed(num % 1_000_000 === 0 ? 0 : 1)}M`;
  if (num >= 1_000) return `$${(num / 1_000).toFixed(0)}K`;
  return `$${num}`;
}

export default function CriteriaSummary({ criteria = {}, strategy = {}, name }) {
  const industries = criteria.industries || [];
  const geos = criteria.geographies || [];
  const states = geos.flatMap((g) => g.states || []);
  const countries = [...new Set(geos.map((g) => g.country).filter(Boolean))];
  const keywords = criteria.keywords || [];
  const rmin = formatMoney(criteria.revenue_min);
  const rmax = formatMoney(criteria.revenue_max);

  const rows = [
    industries.length > 0 && {
      label: "Industries",
      content: (
        <div className="flex flex-wrap gap-1.5">
          {industries.map((i) => (
            <Chip key={i}>{i}</Chip>
          ))}
        </div>
      ),
    },
    (states.length > 0 || countries.length > 0) && {
      label: "Geography",
      content: (
        <div className="flex flex-wrap gap-1.5">
          {countries.map((c) => (
            <Chip key={c}>{c}</Chip>
          ))}
          {states.map((s) => (
            <Chip key={s}>{s}</Chip>
          ))}
        </div>
      ),
    },
    (rmin || rmax) && {
      label: "Revenue band",
      content: (
        <p className="text-sm text-ink-soft">
          {rmin && rmax ? `${rmin} – ${rmax}` : rmin ? `From ${rmin}` : `Up to ${rmax}`}
        </p>
      ),
    },
    criteria.owner_operated != null && {
      label: "Ownership",
      content: (
        <p className="text-sm text-ink-soft">
          {criteria.owner_operated ? "Owner-operated preferred" : "Any ownership profile"}
        </p>
      ),
    },
    criteria.min_years_in_business != null && {
      label: "Business age",
      content: (
        <p className="text-sm text-ink-soft">
          At least {criteria.min_years_in_business} years in business
        </p>
      ),
    },
    keywords.length > 0 && {
      label: "Keywords",
      content: (
        <div className="flex flex-wrap gap-1.5">
          {keywords.map((k) => (
            <Chip key={k}>{k}</Chip>
          ))}
        </div>
      ),
    },
    strategy?.rationale && {
      label: "Rationale",
      content: <p className="text-sm leading-relaxed text-ink-soft">{strategy.rationale}</p>,
    },
    (strategy?.adjacent_segments || []).length > 0 && {
      label: "Adjacent segments",
      content: (
        <div className="flex flex-wrap gap-1.5">
          {strategy.adjacent_segments.map((s) => (
            <Chip key={s}>{s}</Chip>
          ))}
        </div>
      ),
    },
  ].filter(Boolean);

  if (!rows.length) {
    return (
      <p className="text-sm text-ink-mute">No criteria set yet — fill the form or run a search.</p>
    );
  }

  return (
    <div className="border border-line bg-white/60">
      {name && (
        <div className="border-b border-line px-5 py-4">
          <p className="label">Active thesis</p>
          <h3 className="mt-1 font-display text-2xl text-ink">{name}</h3>
        </div>
      )}
      <dl className="divide-y divide-line">
        {rows.map((row) => (
          <div
            key={row.label}
            className="grid gap-2 px-5 py-4 sm:grid-cols-[140px_1fr] sm:items-start"
          >
            <dt className="label pt-0.5">{row.label}</dt>
            <dd>{row.content}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
