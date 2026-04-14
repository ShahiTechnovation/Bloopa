/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg:       "#fdfbf7",
        surface:  "#ffffff",
        elevated: "#f4f0e6",
        border:   "#000000",
        accent:   "#bbf7d0", // Light playful green
        "accent-hover": "#86efac",
        "accent-dim": "#f0fdf4",
        success:  "#93c5fd", // Playful blue
        "success-dim": "#eff6ff",
        danger:   "#fca5a5", // Playful red
        "danger-dim": "#fef2f2",
        warning:  "#fde047", // Playful yellow
        "warning-dim": "#fefce8",
        muted:    "#d4d4d4",
        "text-muted": "#737373",
        "text-primary": "#000000",
        "text-secondary": "#404040",
      },
      fontFamily: {
        display: ["Syne", "sans-serif"],
        sans:    ["DM Sans", "sans-serif"],
        mono:    ["JetBrains Mono", "Fira Code", "Courier New", "monospace"],
        pixel:   ["VT323", "Courier New", "monospace"], // Playful pixel font
        hand:    ["Caveat", "Comic Sans MS", "cursive", "sans-serif"], // Handwriting
      },
      boxShadow: {
        'brutalist-sm': '2px 2px 0px 0px rgba(0,0,0,1)',
        'brutalist': '4px 4px 0px 0px rgba(0,0,0,1)',
        'brutalist-lg': '8px 8px 0px 0px rgba(0,0,0,1)',
      },
      animation: {
        shimmer:      "shimmer 1.5s infinite",
        "flash-green":"flash-green 1.5s ease-out",
        "flash-red":  "flash-red 1.5s ease-out",
        "spin-slow":  "spin 0.8s linear infinite",
        "pulse-dot":  "pulse 2s cubic-bezier(0.4,0,0.6,1) infinite",
        "marquee":    "marquee 20s linear infinite",
      },
      keyframes: {
        shimmer: {
          "0%":   { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
        marquee: {
          "0%": { transform: "translateX(0%)" },
          "100%": { transform: "translateX(-100%)" },
        }
      },
      spacing: {
        "xs": "4px",
        "sm": "8px",
        "md": "16px",
        "lg": "24px",
        "xl": "32px",
        "2xl": "48px",
        "3xl": "64px",
      },
      borderRadius: {
        "card": "12px",
        "input": "8px",
        "badge": "6px",
        "btn": "8px",
      },
    },
  },
  plugins: [],
};
