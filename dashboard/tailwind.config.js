/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        coperniq: {
          blue: '#2563eb',
          dark: '#1e40af',
        },
      },
    },
  },
  plugins: [],
}
