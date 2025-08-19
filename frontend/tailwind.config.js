/** @type {import('tailwindcss').Config} */
export default {
  prefix: 'tw-', // PREFIXO DE SEGURANÇA - Evita conflitos com PrimeVue
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        'inter': ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
