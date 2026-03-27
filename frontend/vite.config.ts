import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // So frontend can call /api/* without CORS hassle in dev
    proxy: {
      '/api': '',
    },
  },
})
