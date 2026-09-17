import { motion, animate } from "framer-motion";
import { useEffect, useState } from "react";

export const pageVariants = {
  initial: { opacity: 0, y: 14 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] },
  },
  exit: { opacity: 0, y: -8, transition: { duration: 0.2 } },
};

export const stagger = {
  animate: { transition: { staggerChildren: 0.06, delayChildren: 0.08 } },
};

export const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] },
  },
};

export function PageShell({ children, className = "" }) {
  return (
    <motion.div
      className={className}
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      {children}
    </motion.div>
  );
}

export function AnimatedNumber({ value, className = "" }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const controls = animate(0, Number(value) || 0, {
      duration: 0.85,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => setDisplay(Math.round(v)),
    });
    return () => controls.stop();
  }, [value]);

  return <span className={className}>{display}</span>;
}

export function ScoreBar({ label, value, tone = "signal" }) {
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  const tones = {
    signal: "bg-signal",
    warm: "bg-warm",
    cool: "bg-cool",
    ink: "bg-ink",
    muted: "bg-ink-mute",
  };
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-faint">
          {label}
        </span>
        <span className="font-mono text-xs font-medium text-ink">{v.toFixed(0)}</span>
      </div>
      <div className="h-[3px] overflow-hidden rounded-sm bg-paper-wash">
        <motion.div
          className={`h-full rounded-sm ${tones[tone] || tones.signal}`}
          initial={{ width: 0 }}
          animate={{ width: `${v}%` }}
          transition={{ duration: 0.85, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
        />
      </div>
    </div>
  );
}

export function ActionBadge({ action }) {
  const map = {
    CONTACT_NOW: "bg-signal-soft text-signal-deep",
    RELATIONSHIP_FIRST: "bg-warm-soft text-warm",
    RESEARCH_MORE: "bg-cool-soft text-cool",
    MONITOR: "bg-paper-wash text-ink-mute",
    DEPRIORITIZE: "bg-danger-soft text-danger",
  };
  return (
    <span className={`action-chip ${map[action] || map.MONITOR}`}>
      {(action || "—").replaceAll("_", " ")}
    </span>
  );
}

export function ErrorState({ error, onRetry }) {
  const network = error?.code === "NETWORK";
  const title = network ? "Backend unreachable" : "Something went wrong";
  return (
    <PageShell className="mx-auto max-w-lg py-20 text-center">
      <p className="label">Connection</p>
      <h2 className="mt-3 font-display text-3xl text-ink">{title}</h2>
      <p className="mt-3 text-sm text-ink-mute">{error?.message || "Unknown error"}</p>
      {onRetry && (
        <button type="button" className="btn-primary mt-8" onClick={onRetry}>
          Retry
        </button>
      )}
    </PageShell>
  );
}

export function Loading() {
  return (
    <div className="flex items-center justify-center py-24">
      <motion.div
        className="h-8 w-8 rounded-full border-2 border-line border-t-signal"
        animate={{ rotate: 360 }}
        transition={{ duration: 0.9, repeat: Infinity, ease: "linear" }}
      />
    </div>
  );
}

export function SectionLabel({ children, aside }) {
  return (
    <div className="mb-5 flex items-end justify-between gap-4">
      <h2 className="label">{children}</h2>
      {aside}
    </div>
  );
}
