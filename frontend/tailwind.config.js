/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        obsidian: {
          900: '#0B0F17',
          800: '#111827',
          700: '#1F2937',
        },
        cyber: {
          violet: '#8B5CF6',
          emerald: '#10B981',
          cyan: '#06B6D4',
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
