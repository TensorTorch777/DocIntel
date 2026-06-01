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
        midnight: "#000000",
        charcoal: "#1a1a1a",
        slate: "#7d7d7d",
        "ghost-ash": "#f6f6f4",
        smoke: "#ffffff",
        accent: "#ff8400",
      },
      fontFamily: {
        display: [
          "var(--font-recoleta)",
          "Playfair Display",
          "Georgia",
          "serif",
        ],
        body: [
          "var(--font-grotesk)",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
      },
      fontSize: {
        caption: ["13px", { lineHeight: "1.4" }],
        body: ["15px", { lineHeight: "1.6" }],
        subheading: ["21px", { lineHeight: "1.3", fontWeight: "300" }],
        "heading-sm": ["24px", { lineHeight: "1.25" }],
        heading: ["36px", { lineHeight: "1" }],
        "heading-lg": ["47px", { lineHeight: "1.1" }],
        display: ["61px", { lineHeight: "1.1" }],
      },
      borderRadius: {
        input: "4px",
        link: "12px",
        card: "16px",
        large: "38px",
        btn: "100px",
      },
      spacing: {
        section: "50px",
        element: "20px",
        card: "22px",
      },
      backgroundImage: {
        iridescent: "linear-gradient(90deg, #feed7a, #ff8400, #df91f7)",
        "iridescent-vertical":
          "linear-gradient(180deg, #feed7a 0%, #ff8400 45%, #df91f7 100%)",
      },
      boxShadow: {
        inset: "rgba(255, 255, 255, 0.25) 0px 0.636826px 3.82096px 0px inset",
      },
      maxWidth: {
        chat: "52rem",
      },
      animation: {
        shimmer: "shimmer 3s ease-in-out infinite",
        blink: "blink 1s step-end infinite",
      },
      keyframes: {
        shimmer: {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
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
