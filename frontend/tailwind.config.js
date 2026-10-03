/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#07090c",
        panel: "#0e1217",
        panel2: "#131820",
        line: "#1f2630",
        line2: "#2a323e",
        ink: "#e6e8eb",
        ink2: "#a3a9b3",
        mute: "#6b7380",
        good: "#22c55e",
        bad: "#ef4444",
        warn: "#fab219",
        accent: "#3987e5",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
