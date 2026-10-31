import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  server: {
    // In development the API runs on :8000; the proxy avoids CORS entirely
    proxy: { '/api': 'http://localhost:8000' },
  },
  build: {
    // Recharts alone is about 580 kB minified (160 kB gzipped); that is expected
    chunkSizeWarningLimit: 650,
    rollupOptions: {
      // Recharts is the bulk of the bundle; its own chunk caches across app releases
      output: { manualChunks: { recharts: ['recharts'] } },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
})
