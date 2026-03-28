import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  important: "#__next",  // needed for MUI + Tailwind coexistence
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#eff6ff",
          500: "#3B82F6",
          600: "#2563EB",
          700: "#1D4ED8",
        },
        neutral: {
          50: "#f8f9fa",
          200: "#e9ecef",
          600: "#64748b",
          900: "#2c3e50",
        },
      },
      fontFamily: {
        sans: ["Roboto", "Arial", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
