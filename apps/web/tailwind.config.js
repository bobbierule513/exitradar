/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0A1628",
        "ink-soft": "#1C2A3A",
        "ink-mute": "#5A6B7D",
        "ink-faint": "#8A97A6",
        paper: "#E9EEF3",
        "paper-elev": "#F5F7FA",
        "paper-wash": "#DDE5EE",
        line: "#C8D2DC",
        "line-strong": "#9AABBC",
        signal: "#0B6E5F",
        "signal-soft": "#D4EDE7",
        "signal-deep": "#084F44",
        warm: "#8B5A1A",
        "warm-soft": "#F3E6D0",
        cool: "#2B5A8A",
        "cool-soft": "#D6E4F2",
        danger: "#8B2E2E",
        "danger-soft": "#F0DADA",
      },
      fontFamily: {
        display: ['"Instrument Serif"', "Georgia", "serif"],
        sans: ['"Outfit"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        desk: "0 1px 0 rgba(10,22,40,0.06), 0 18px 40px -24px rgba(10,22,40,0.35)",
        lift: "0 12px 32px -16px rgba(10,22,40,0.28)",
      },
      backgroundImage: {
        "desk-grid":
          "linear-gradient(to right, rgba(10,22,40,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(10,22,40,0.04) 1px, transparent 1px)",
        "hero-wash":
          "radial-gradient(1200px 500px at 10% -10%, rgba(11,110,95,0.14), transparent 55%), radial-gradient(900px 420px at 90% 0%, rgba(43,90,138,0.10), transparent 50%)",
      },
      backgroundSize: {
        desk: "48px 48px",
      },
      letterSpacing: {
        brand: "0.02em",
      },
    },
  },
  plugins: [],
};
