/** @type {import('tailwindcss').Config} */

module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      gridTemplateRows: {
        layout: "auto auto minmax(0, 1fr)",
        "mobile-inner": "minmax(0, 2fr) minmax(0, 1fr)",
        "layout-one": "minmax(0, 1fr) auto",
      },
      animation: {
        "spin-slow": "spin 3s linear infinite",
      },
      colors: {
        bluegrey: "RGB(90, 122, 158)",
      },
    },
  },
  plugins: [],
};
