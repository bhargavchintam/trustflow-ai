import type { Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a0c",
        surface: "#101013",
        panel: "#15161a",
        elevated: "#1a1c22",
        muted: "#8b8f96",
        subtle: "#5f636a",
        border: "#23252c",
        "border-strong": "#2d3038",
        accent: "#7c5cff",
        "accent-soft": "#9c84ff",
        ok: "#22c55e",
        warn: "#eab308",
        deny: "#ef4444",
        info: "#3b82f6",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
