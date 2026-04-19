/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    environmentOptions: {
      jsdom: { url: 'http://localhost:5173' },
    },
    setupFiles: './src/test-setup.ts',
    globals: true,
    // Playwright specs live under tests/e2e/ and must NOT be loaded by vitest.
    // Keep the default include but carve the E2E tree out explicitly.
    exclude: ['node_modules', 'dist', 'tests/e2e/**'],
  },
})
