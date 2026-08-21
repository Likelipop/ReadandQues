/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      colors: {
        obsidian: {
          950: '#04070D',
          900: '#080C14',
          850: '#0D121F',
          800: '#131B2E',
          700: '#1E293B',
          600: '#334155',
        },
        cyber: {
          violet: '#7C3AED',
          indigo: '#6366F1',
          cyan: '#06B6D4',
          emerald: '#10B981',
          amber: '#F59E0B',
          rose: '#F43F5E',
        },
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.45)',
        'glow-violet': '0 0 30px -4px rgba(124, 58, 237, 0.45)',
        'glow-cyan': '0 0 30px -4px rgba(6, 182, 212, 0.45)',
        'glow-emerald': '0 0 30px -4px rgba(16, 185, 129, 0.45)',
        'inner-specular': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.08)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
