import { motion } from "framer-motion";
import { useMemo } from "react";

const EASE = [0.22, 1, 0.36, 1];

/** Polar point for radar chart (angle in degrees, value 0–100). */
function polar(cx, cy, r, angleDeg) {
  const a = ((angleDeg - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
}

/**
 * 5-axis opportunity radar — pure SVG.
 * axes: Fit, Seller, Timing, Access, Competition
 */
export function OpportunityRadar({
  fit = 0,
  seller = 0,
  timing = 0,
  access = 0,
  competition = 0,
  size = 280,
  label = "Lead profile",
}) {
  const cx = size / 2;
  const cy = size / 2;
  const maxR = size * 0.36;
  const axes = [
    { key: "fit", label: "Fit", value: fit },
    { key: "seller", label: "Seller", value: seller },
    { key: "timing", label: "Timing", value: timing },
    { key: "access", label: "Access", value: access },
    { key: "comp", label: "Comp+", value: competition },
  ];
  const n = axes.length;
  const step = 360 / n;

  const rings = [0.25, 0.5, 0.75, 1];
  const gridPolys = rings.map((t) =>
    axes
      .map((_, i) => polar(cx, cy, maxR * t, i * step).join(","))
      .join(" ")
  );

  const dataPoints = axes.map((ax, i) =>
    polar(cx, cy, maxR * (Math.max(0, Math.min(100, ax.value)) / 100), i * step)
  );
  const dataPath = dataPoints.map((p, i) => `${i === 0 ? "M" : "L"}${p[0]},${p[1]}`).join(" ") + " Z";

  return (
    <div className="relative">
      <p className="label mb-3">{label}</p>
      <svg
        viewBox={`0 0 ${size} ${size}`}
        className="mx-auto w-full max-w-[300px]"
        role="img"
        aria-label="Opportunity component radar chart"
      >
        {gridPolys.map((pts, i) => (
          <polygon
            key={i}
            points={pts}
            fill="none"
            stroke="#C8D2DC"
            strokeWidth={i === gridPolys.length - 1 ? 1.25 : 0.75}
            opacity={0.9}
          />
        ))}
        {axes.map((ax, i) => {
          const [x, y] = polar(cx, cy, maxR, i * step);
          const [lx, ly] = polar(cx, cy, maxR + 22, i * step);
          return (
            <g key={ax.key}>
              <line x1={cx} y1={cy} x2={x} y2={y} stroke="#C8D2DC" strokeWidth="0.75" />
              <text
                x={lx}
                y={ly}
                textAnchor="middle"
                dominantBaseline="middle"
                className="fill-ink-faint"
                style={{ fontSize: 10, fontFamily: "JetBrains Mono, monospace" }}
              >
                {ax.label}
              </text>
            </g>
          );
        })}
        <motion.polygon
          points={dataPoints.map((p) => p.join(",")).join(" ")}
          fill="rgba(11,110,95,0.18)"
          stroke="#0B6E5F"
          strokeWidth="2"
          initial={{ opacity: 0, scale: 0.6 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, ease: EASE }}
          style={{ transformOrigin: `${cx}px ${cy}px` }}
        />
        {dataPoints.map(([x, y], i) => (
          <motion.circle
            key={i}
            cx={x}
            cy={y}
            r="3.5"
            fill="#0B6E5F"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.35 + i * 0.05 }}
          />
        ))}
        {/* invisible path for a11y / future spark */}
        <path d={dataPath} fill="none" stroke="none" />
      </svg>
      <div className="mt-2 grid grid-cols-5 gap-1 text-center font-mono text-[10px] text-ink-mute">
        {axes.map((ax) => (
          <div key={ax.key}>
            <div className="text-ink font-medium">{Math.round(ax.value)}</div>
            <div className="uppercase tracking-wider text-ink-faint">{ax.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Horizontal ranking bars for opportunity scores. */
export function RankingChart({ opportunities = [], height = 200 }) {
  const rows = useMemo(
    () =>
      (opportunities || []).slice(0, 5).map((o) => ({
        id: o.id,
        name: o.company?.canonical_name || "Company",
        score: Number(o.opportunity_score) || 0,
        short: (o.company?.canonical_name || "?").split(" ")[0],
      })),
    [opportunities]
  );
  const max = Math.max(100, ...rows.map((r) => r.score), 1);
  const rowH = height / Math.max(rows.length, 1);

  if (!rows.length) {
    return <p className="text-sm text-ink-mute">No ranked opportunities yet.</p>;
  }

  return (
    <div>
      <p className="label mb-3">Score ladder</p>
      <svg
        viewBox={`0 0 400 ${height}`}
        className="w-full"
        role="img"
        aria-label="Opportunity score ranking chart"
      >
        {rows.map((r, i) => {
          const y = i * rowH + 8;
          const barW = (r.score / max) * 280;
          return (
            <g key={r.id}>
              <text
                x="0"
                y={y + 14}
                className="fill-ink-mute"
                style={{ fontSize: 11, fontFamily: "Outfit, sans-serif" }}
              >
                {r.short.length > 12 ? `${r.short.slice(0, 11)}…` : r.short}
              </text>
              <rect x="100" y={y} width="280" height="18" fill="#DDE5EE" rx="2" />
              <motion.rect
                x="100"
                y={y}
                height="18"
                rx="2"
                fill={i === 0 ? "#0B6E5F" : "#1C2A3A"}
                initial={{ width: 0 }}
                animate={{ width: barW }}
                transition={{ duration: 0.8, delay: i * 0.06, ease: EASE }}
              />
              <text
                x={108 + barW}
                y={y + 13}
                className="fill-ink"
                style={{ fontSize: 11, fontFamily: "JetBrains Mono, monospace", fontWeight: 500 }}
              >
                {Math.round(r.score)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/** Action mix as an animated donut. */
export function ActionMixChart({ opportunities = [], size = 180 }) {
  const counts = useMemo(() => {
    const map = {
      CONTACT_NOW: 0,
      RELATIONSHIP_FIRST: 0,
      RESEARCH_MORE: 0,
      MONITOR: 0,
      DEPRIORITIZE: 0,
    };
    for (const o of opportunities || []) {
      const a = o.recommendation?.action;
      if (a && map[a] !== undefined) map[a] += 1;
      else if (a) map.MONITOR += 1;
    }
    return Object.entries(map)
      .filter(([, v]) => v > 0)
      .map(([key, value]) => ({ key, value }));
  }, [opportunities]);

  const total = counts.reduce((s, c) => s + c.value, 0) || 1;
  const colors = {
    CONTACT_NOW: "#0B6E5F",
    RELATIONSHIP_FIRST: "#8B5A1A",
    RESEARCH_MORE: "#2B5A8A",
    MONITOR: "#8A97A6",
    DEPRIORITIZE: "#8B2E2E",
  };

  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.36;
  const stroke = size * 0.12;

  let angle = -90;
  const arcs = counts.map((c) => {
    const sweep = (c.value / total) * 360;
    const start = angle;
    angle += sweep;
    return { ...c, start, sweep };
  });

  function arcPath(startDeg, sweepDeg) {
    if (sweepDeg >= 359.9) {
      // full circle
      return null;
    }
    const start = polar(cx, cy, r, startDeg);
    const end = polar(cx, cy, r, startDeg + sweepDeg);
    const large = sweepDeg > 180 ? 1 : 0;
    return `M ${start[0]} ${start[1]} A ${r} ${r} 0 ${large} 1 ${end[0]} ${end[1]}`;
  }

  return (
    <div>
      <p className="label mb-3">Action mix</p>
      <div className="flex items-center gap-5">
        <svg
          viewBox={`0 0 ${size} ${size}`}
          className="h-[140px] w-[140px] shrink-0"
          role="img"
          aria-label="Next-action mix donut chart"
        >
          <circle cx={cx} cy={cy} r={r} fill="none" stroke="#DDE5EE" strokeWidth={stroke} />
          {arcs.map((a, i) => {
            if (a.sweep >= 359.9) {
              return (
                <motion.circle
                  key={a.key}
                  cx={cx}
                  cy={cy}
                  r={r}
                  fill="none"
                  stroke={colors[a.key]}
                  strokeWidth={stroke}
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.9, delay: i * 0.05, ease: EASE }}
                />
              );
            }
            return (
              <motion.path
                key={a.key}
                d={arcPath(a.start, a.sweep)}
                fill="none"
                stroke={colors[a.key]}
                strokeWidth={stroke}
                strokeLinecap="butt"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ duration: 0.75, delay: i * 0.08, ease: EASE }}
              />
            );
          })}
          <text
            x={cx}
            y={cy - 4}
            textAnchor="middle"
            style={{ fontSize: 22, fontFamily: "JetBrains Mono, monospace", fontWeight: 500 }}
            className="fill-ink"
          >
            {total}
          </text>
          <text
            x={cx}
            y={cy + 14}
            textAnchor="middle"
            style={{ fontSize: 9, letterSpacing: "0.12em", fontFamily: "Outfit, sans-serif" }}
            className="fill-ink-faint"
          >
            TOTAL
          </text>
        </svg>
        <ul className="space-y-2 text-xs">
          {arcs.map((a) => (
            <li key={a.key} className="flex items-center gap-2 text-ink-mute">
              <span
                className="inline-block h-2 w-2 rounded-sm"
                style={{ background: colors[a.key] }}
              />
              <span className="uppercase tracking-wider">
                {a.key.replaceAll("_", " ")}
              </span>
              <span className="ml-auto font-mono text-ink">{a.value}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/** Sparkline of opportunity scores as a trend / distribution curve. */
export function MomentumSparkline({ opportunities = [], width = 420, height = 120 }) {
  const scores = useMemo(
    () =>
      [...(opportunities || [])]
        .map((o) => Number(o.opportunity_score) || 0)
        .sort((a, b) => b - a),
    [opportunities]
  );

  if (scores.length < 2) {
    return null;
  }

  const pad = 12;
  const w = width - pad * 2;
  const h = height - pad * 2;
  const min = Math.min(...scores, 40);
  const max = Math.max(...scores, 100);
  const pts = scores.map((s, i) => {
    const x = pad + (i / (scores.length - 1)) * w;
    const y = pad + h - ((s - min) / (max - min || 1)) * h;
    return [x, y];
  });
  const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0]},${p[1]}`).join(" ");
  const area =
    line +
    ` L${pts[pts.length - 1][0]},${pad + h} L${pts[0][0]},${pad + h} Z`;

  return (
    <div>
      <div className="mb-3 flex items-end justify-between">
        <p className="label">Universe curve</p>
        <p className="font-mono text-[10px] text-ink-faint">
          high {Math.round(scores[0])} → low {Math.round(scores[scores.length - 1])}
        </p>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        role="img"
        aria-label="Opportunity score distribution sparkline"
      >
        <line
          x1={pad}
          y1={pad + h}
          x2={pad + w}
          y2={pad + h}
          stroke="#C8D2DC"
          strokeWidth="1"
        />
        <motion.path
          d={area}
          fill="rgba(43,90,138,0.12)"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6 }}
        />
        <motion.path
          d={line}
          fill="none"
          stroke="#2B5A8A"
          strokeWidth="2.25"
          strokeLinejoin="round"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1, ease: EASE }}
        />
        {pts.map(([x, y], i) => (
          <motion.circle
            key={i}
            cx={x}
            cy={y}
            r={i === 0 ? 4 : 2.5}
            fill={i === 0 ? "#0B6E5F" : "#2B5A8A"}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 + i * 0.05 }}
          />
        ))}
      </svg>
    </div>
  );
}
