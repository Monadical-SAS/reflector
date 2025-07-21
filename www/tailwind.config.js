/** @type {import('tailwindcss').Config} */

module.exports = {
  corePlugins: {
    preflight: false,
  },
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      gridTemplateRows: {
        "layout-topbar": "auto minmax(0,1fr)",
        "mobile-inner": "minmax(0, 2fr) minmax(0, 1fr)",
        "layout-one": "minmax(0, 1fr) auto",
      },
      animation: {
        "spin-slow": "spin 3s linear infinite",
        "wave-quiet": "wave-quiet 1.2s ease-in-out infinite",
        "wave-normal": "wave-normal 1.2s ease-in-out infinite",
        "wave-loud": "wave-loud 1.2s ease-in-out infinite",
      },
      keyframes: {
        "wave-quiet": {
          "25%": {
            transform: "scaleY(.6)",
          },
          "50%": {
            transform: "scaleY(.4)",
          },
          "75%": {
            transform: "scaleY(.4)",
          },
        },
        "wave-normal": {
          "25%": {
            transform: "scaleY(1)",
          },
          "50%": {
            transform: "scaleY(.4)",
          },
          "75%": {
            transform: "scaleY(.6)",
          },
        },
        "wave-loud": {
          "25%": {
            transform: "scaleY(1)",
          },
          "50%": {
            transform: "scaleY(.4)",
          },
          "75%": {
            transform: "scaleY(1.2)",
          },
        },
      },
      colors: {
        bluegrey: "RGB(90, 122, 158)",
      },
    },
  },
  plugins: [],
};
