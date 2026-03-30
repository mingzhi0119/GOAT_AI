import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // './' makes all asset paths relative so the SPA works behind any sub-path
  // proxy (JupyterHub server-proxy, nginx /mingzhi/, etc.) without URL rewriting.
  base: './',
  server: {
    // Dev-mode proxy: forward /api/* to FastAPI on :8002
    proxy: {
      '/api': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // Warn on chunks > 500 kB
    chunkSizeWarningLimit: 500,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts'],
  },
})
