import type { Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0b0d10",
        panel: "#15181d",
        muted: "#9aa0a6",
        border: "#262a31",
        accent: "#7c5cff",
        ok: "#16a34a",
        warn: "#eab308",
        deny: "#ef4444",
      },
    },
  },
  plugins: [],
} satisfies Config;
