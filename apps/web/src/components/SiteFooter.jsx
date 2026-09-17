import { Link } from "react-router-dom";
import { useWorkspace } from "../lib/workspace";

const product = [
  { to: "/", label: "Radar" },
  { to: "/opportunities", label: "Pipeline" },
  { to: "/thesis", label: "Thesis" },
];

const stack = [
  "FastAPI · Postgres",
  "Evidence-first scoring",
  "Robots-aware discovery",
];

export default function SiteFooter() {
  const { withContext } = useWorkspace();
  const year = new Date().getFullYear();

  return (
    <footer className="relative z-10 mt-auto border-t border-line bg-ink text-paper-elev">
      <div className="mx-auto max-w-[1200px] px-5 py-12 md:px-8 md:py-14">
        <div className="grid gap-10 md:grid-cols-12 md:gap-8">
          <div className="md:col-span-5">
            <Link
              to={withContext("/")}
              aria-label="ExitRadar home"
              className="inline-block font-display text-3xl tracking-brand text-white transition hover:text-signal-soft"
            >
              ExitRadar
            </Link>
            <p className="mt-3 max-w-sm text-sm leading-relaxed text-white/55">
              Acquisition opportunity engine for searchers — thesis in, ranked deals out,
              with evidence on every score.
            </p>
            <p className="mt-6 font-mono text-[10px] uppercase tracking-[0.18em] text-white/35">
              Caprae assessment · v1
            </p>
          </div>

          <div className="md:col-span-3">
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-white/40">
              Product
            </p>
            <ul className="mt-4 space-y-2.5">
              {product.map((item) => (
                <li key={item.to}>
                  <Link
                    to={withContext(item.to)}
                    className="text-sm text-white/70 transition hover:text-white"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="md:col-span-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-white/40">
              Built for searchers
            </p>
            <ul className="mt-4 space-y-2.5">
              {stack.map((line) => (
                <li key={line} className="text-sm text-white/70">
                  {line}
                </li>
              ))}
            </ul>
            <a
              href="https://www.saasquatchleads.com/"
              target="_blank"
              rel="noreferrer"
              className="mt-5 inline-block text-sm text-signal-soft transition hover:text-white"
            >
              Inspired by SaaSquatch Leads →
            </a>
          </div>
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-6">
          <p className="font-mono text-[11px] text-white/35">
            © {year} ExitRadar. Ethical discovery · no CAPTCHA bypass.
          </p>
          <p className="font-mono text-[11px] text-white/35">
            Scores are prioritization weights — not sale probabilities.
          </p>
        </div>
      </div>
    </footer>
  );
}
