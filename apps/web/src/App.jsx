import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import CommandCenter from "./pages/CommandCenter";
import Opportunities from "./pages/Opportunities";
import CompanyPage from "./pages/CompanyPage";
import ThesisPage from "./pages/ThesisPage";
import SiteFooter from "./components/SiteFooter";
import { WorkspaceProvider, useWorkspace } from "./lib/workspace";

const nav = [
  { to: "/", label: "Radar", end: true },
  { to: "/opportunities", label: "Pipeline" },
  { to: "/thesis", label: "Thesis" },
];

function Shell() {
  const location = useLocation();
  const { withContext, theses, thesisId, setThesisId, isLoading } = useWorkspace();

  return (
    <div className="shell flex min-h-screen flex-col">
      <div className="shell-bg" />
      <div className="shell-grid" />

      <header className="sticky top-0 z-30 border-b border-line/80 bg-paper/75 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1200px] items-center justify-between gap-6 px-5 py-4 md:px-8">
          <NavLink
            to={withContext("/")}
            end
            aria-label="ExitRadar home"
            className="group relative z-10 flex cursor-pointer items-baseline gap-3"
          >
            <span className="font-display text-[1.65rem] leading-none tracking-brand text-ink transition group-hover:text-signal-deep">
              ExitRadar
            </span>
            <span className="hidden font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint sm:inline">
              Opportunity Engine
            </span>
          </NavLink>

          <div className="flex items-center gap-3">
            {theses.length > 1 && (
              <label className="flex items-center gap-2">
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">
                  Thesis
                </span>
                <select
                  className="input max-w-[220px] py-1.5 text-xs"
                  value={thesisId}
                  disabled={isLoading}
                  onChange={(e) => setThesisId(e.target.value)}
                >
                  {theses.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <nav className="flex items-center gap-1">
              {nav.map((item) => (
                <NavLink
                  key={item.to}
                  to={withContext(item.to)}
                  end={item.end}
                  className={({ isActive }) =>
                    `relative px-3 py-2 text-sm font-medium transition ${
                      isActive ? "text-ink" : "text-ink-mute hover:text-ink"
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      {item.label}
                      {isActive && (
                        <motion.span
                          layoutId="nav-underline"
                          className="absolute inset-x-3 -bottom-[17px] h-[2px] bg-signal"
                          transition={{ type: "spring", stiffness: 380, damping: 32 }}
                        />
                      )}
                    </>
                  )}
                </NavLink>
              ))}
            </nav>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1200px] flex-1 px-5 py-8 md:px-8 md:py-10">
        <AnimatePresence mode="sync">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
          >
            <Routes location={location}>
              <Route path="/" element={<CommandCenter />} />
              <Route path="/opportunities" element={<Opportunities />} />
              <Route path="/companies/:companyId" element={<CompanyPage />} />
              <Route path="/thesis" element={<ThesisPage />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </main>

      <SiteFooter />
    </div>
  );
}

export default function App() {
  return (
    <WorkspaceProvider>
      <Shell />
    </WorkspaceProvider>
  );
}
