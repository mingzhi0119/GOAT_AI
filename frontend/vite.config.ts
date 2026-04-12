import { defineConfig } from 'vitest/config'
import { loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.VITE_GOAT_API_PROXY_TARGET || 'http://localhost:62606'

  return {
    plugins: [react()],
    // './' makes all asset paths relative so the SPA works behind any sub-path
    // proxy (JupyterHub server-proxy, nginx /mingzhi/, etc.) without URL rewriting.
    base: './',
    server: {
      // Dev-mode proxy: forward /api/* to FastAPI.
      proxy: {
        '/api': {
          target: apiProxyTarget,
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
      include: ['src/**/*.{test,spec}.{ts,tsx}', 'scripts/**/*.test.mjs'],
      exclude: ['e2e/**'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'lcov'],
        exclude: ['src/__tests__/**', 'src/**/*.d.ts'],
        thresholds: {
          lines: 70,
          functions: 70,
          statements: 70,
          branches: 65,
        },
      },
    },
  }
})
