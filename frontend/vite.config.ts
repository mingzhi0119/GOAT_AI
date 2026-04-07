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
    // Keep heavy visualization code in its own async chunk instead of the main app bundle.
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/echarts-for-react')) {
            return 'charts-react'
          }
          if (id.includes('node_modules/echarts/core')) {
            return 'charts-core'
          }
          if (id.includes('node_modules/echarts/charts')) {
            return 'charts-series'
          }
          if (id.includes('node_modules/echarts/components')) {
            return 'charts-components'
          }
          if (id.includes('node_modules/echarts')) {
            return 'charts-engine'
          }
          if (id.includes('node_modules/zrender')) {
            return 'charts-renderer'
          }
          return undefined
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts'],
  },
})
