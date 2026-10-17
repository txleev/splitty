import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// The Room API. In development the dev server forwards /api/* to it, with the /api prefix removed.
const apiTarget = process.env.SPLITTY_API ?? 'http://127.0.0.1:8001'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
  },
})
