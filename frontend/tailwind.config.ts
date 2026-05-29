import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "midnight-ink": "#202020",
        "cloud-canvas": "#f5f5f5",
        "paper-white": "#ffffff",
        "muted-ash": "#333333",
        "ghost-border": "#f7f5fd",
        "electric-violet": "#5757f8",
      },
      fontFamily: {
        display: ["var(--font-montserrat)", "ui-sans-serif", "system-ui", "sans-serif"],
        body: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      fontSize: {
        caption: ["14px", { lineHeight: "1.2" }],
        body: ["16px", { lineHeight: "1.4" }],
        subheading: ["18px", { lineHeight: "1.43" }],
        "heading-sm": ["20px", { lineHeight: "1.43" }],
        heading: ["26px", { lineHeight: "1.2", letterSpacing: "-0.52px" }],
        "heading-lg": ["36px", { lineHeight: "1", letterSpacing: "-0.72px" }],
        display: ["48px", { lineHeight: "0.97", letterSpacing: "-0.96px" }],
      },
      borderRadius: {
        input: "10px",
        card: "8px",
        image: "12px",
        pill: "9999px",
      },
      maxWidth: {
        page: "1400px",
      },
      spacing: {
        section: "40px",
        element: "24px",
        card: "20px",
      },
      backgroundImage: {
        "grid-pattern":
          "radial-gradient(circle, #20202012 1px, transparent 1px)",
      },
      backgroundSize: {
        grid: "24px 24px",
      },
      animation: {
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
        blink: "blink 1s step-end infinite",
      },
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
