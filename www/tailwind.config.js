/** @type {import('tailwindcss').Config} */

// 8 margin main container Top + 40 height header + 16 margin bottom header + 80 recorder
const dashboardStart = 144;

// 8 margin main container Top + 40 height header + 16 margin bottom header + 80 recorder
const dashboardStartMd = 144;

// 16 margin main container Top + 64 height header + 16 margin bottom header + 80 recorder
const dashboardStartLg = 176;

module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      height: {
        "outer-dashboard": `calc(100svh - ${dashboardStart}px)`,
        "outer-dashboard-md": `calc(100svh - ${dashboardStartMd + 34}px)`,
        "outer-dashboard-lg": `calc(100svh - ${dashboardStartLg}px)`,
      },
    },
  },
  plugins: [],
};
