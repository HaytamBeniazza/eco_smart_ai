/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        'eco-green': '#10b981',
        'eco-blue': '#3b82f6',
        'eco-yellow': '#f59e0b',
        'eco-gray': '#6b7280'
      }
    },
  },
  plugins: [],
} 